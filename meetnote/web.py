"""HTTP routes for uploading audio and retrieving job results."""

import uuid
from pathlib import Path

from flask import Blueprint, Response, current_app, jsonify, render_template, request
from werkzeug.utils import secure_filename

from .services.pipeline import process_job
from .storage.results import read_result


web = Blueprint("web", __name__)


@web.get("/")
def index():
    return render_template("index.html")


@web.post("/upload")
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Không tìm thấy file trong request."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Chưa chọn file."}), 400

    extension = Path(file.filename).suffix.lower().lstrip(".")
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    if extension not in allowed:
        return jsonify({
            "error": "Định dạng file không được hỗ trợ. Hỗ trợ: "
            + ", ".join(sorted(allowed))
        }), 400

    engine = request.form.get("engine", "whisper")
    if engine not in {"whisper", "gemma"}:
        return jsonify({"error": "Engine transcribe không hợp lệ."}), 400

    capacity = current_app.extensions["meetnote.capacity"]
    if not capacity.acquire(blocking=False):
        return jsonify({"error": "Hàng đợi đang đầy. Vui lòng thử lại sau."}), 429

    job_id = str(uuid.uuid4())
    filename = secure_filename(file.filename) or f"audio.{extension}"
    upload_path = Path(current_app.config["UPLOAD_DIR"]) / f"{job_id}.{extension}"
    repository = current_app.extensions["meetnote.jobs"]
    executor = current_app.extensions["meetnote.executor"]
    job_created = False
    settings = {
        key: current_app.config[key]
        for key in (
            "TEMP_DIR",
            "RESULTS_DIR",
            "SEGMENT_MINUTES",
            "SUMMARY_CHUNK_CHARS",
            "FFMPEG_BINARY",
            "WHISPER_LANGUAGE",
            "WHISPER_MODEL",
            "WHISPER_DEVICE",
            "OLLAMA_BASE_URL",
            "OLLAMA_MODEL",
            "OLLAMA_TIMEOUT_SECONDS",
        )
    }

    try:
        file.save(str(upload_path))
        if upload_path.stat().st_size == 0:
            upload_path.unlink(missing_ok=True)
            capacity.release()
            return jsonify({"error": "File audio rỗng."}), 400

        repository.create(job_id, filename, engine)
        job_created = True
        future = executor.submit(process_job, job_id, str(upload_path), engine, repository, settings)
        future.add_done_callback(lambda _future: capacity.release())
    except Exception:
        capacity.release()
        upload_path.unlink(missing_ok=True)
        if job_created:
            try:
                repository.update(
                    job_id,
                    status="error",
                    message="Không thể khởi chạy job. Hãy tải file lên lại.",
                )
            except Exception:
                current_app.logger.exception("Could not record rejected job %s", job_id)
        current_app.logger.exception("Could not queue upload %s", job_id)
        return jsonify({"error": "Không thể đưa file vào hàng đợi xử lý."}), 500

    return jsonify({"job_id": job_id, "status": "started"}), 202


@web.get("/status/<job_id>")
def job_status(job_id: str):
    repository = current_app.extensions["meetnote.jobs"]
    job = repository.get(job_id)
    if job is None:
        return jsonify({"error": "Không tìm thấy job."}), 404

    response = {"status": job["status"], "message": job["message"]}
    if job["status"] == "completed" and job["result_path"]:
        try:
            response.update(read_result(job["result_path"]))
        except (OSError, ValueError):
            current_app.logger.exception("Could not read result for job %s", job_id)
            return jsonify({"error": "Không đọc được kết quả đã lưu."}), 500
    return jsonify(response)


@web.get("/jobs")
def recent_jobs():
    jobs = current_app.extensions["meetnote.jobs"].list_recent()
    return jsonify({"jobs": jobs})


@web.get("/health")
def health():
    current_app.extensions["meetnote.jobs"].ping()
    return jsonify({"status": "ok"})


@web.get("/results/<job_id>/<kind>")
def download_result(job_id: str, kind: str):
    if kind not in {"minutes", "transcript"}:
        return jsonify({"error": "Loại kết quả không hợp lệ."}), 404

    job = current_app.extensions["meetnote.jobs"].get(job_id)
    if job is None:
        return jsonify({"error": "Không tìm thấy job."}), 404
    if job["status"] != "completed" or not job["result_path"]:
        return jsonify({"error": "Kết quả chưa sẵn sàng."}), 409

    try:
        content = read_result(job["result_path"])[kind]
    except (OSError, ValueError, KeyError):
        current_app.logger.exception("Could not read %s for job %s", kind, job_id)
        return jsonify({"error": "Không đọc được kết quả đã lưu."}), 500

    suffix = "md" if kind == "minutes" else "txt"
    return Response(
        content,
        mimetype="text/markdown" if kind == "minutes" else "text/plain",
        headers={"Content-Disposition": f'attachment; filename="{job_id}-{kind}.{suffix}"'},
    )
