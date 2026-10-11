"""Flask application factory for MeetNote."""

import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import BoundedSemaphore

from flask import Flask

from .config import Config
from .storage.jobs import JobsRepository
from .web import web


def create_app(config_override: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    if config_override:
        app.config.update(config_override)

        if "DATA_DIR" in config_override:
            data_dir = Path(app.config["DATA_DIR"])
            if "UPLOAD_DIR" not in config_override:
                app.config["UPLOAD_DIR"] = data_dir / "uploads"
            if "TEMP_DIR" not in config_override:
                app.config["TEMP_DIR"] = data_dir / "temp"
            if "RESULTS_DIR" not in config_override:
                app.config["RESULTS_DIR"] = data_dir / "results"
            if "DATABASE" not in config_override:
                app.config["DATABASE"] = data_dir / "meetnote.sqlite3"

    if app.config["SEGMENT_MINUTES"] < 1:
        raise ValueError("MEETNOTE_SEGMENT_MINUTES phải từ 1 trở lên.")
    if app.config["SUMMARY_CHUNK_CHARS"] < 1000:
        raise ValueError("MEETNOTE_SUMMARY_CHUNK_CHARS phải từ 1000 trở lên.")
    if app.config["MAX_CONTENT_LENGTH"] < 1:
        raise ValueError("MEETNOTE_MAX_UPLOAD_BYTES phải lớn hơn 0.")

    for key in ("DATA_DIR", "UPLOAD_DIR", "TEMP_DIR", "RESULTS_DIR"):
        app.config[key] = str(app.config[key])

    for key in ("DATA_DIR", "UPLOAD_DIR", "TEMP_DIR", "RESULTS_DIR"):
        Path(app.config[key]).mkdir(parents=True, exist_ok=True)

    repository = JobsRepository(app.config["DATABASE"])
    for job_id in repository.fail_interrupted_jobs():
        for upload in Path(app.config["UPLOAD_DIR"]).glob(f"{job_id}.*"):
            upload.unlink(missing_ok=True)
        shutil.rmtree(Path(app.config["TEMP_DIR"]) / job_id, ignore_errors=True)
        Path(app.config["RESULTS_DIR"], f"{job_id}.json.tmp").unlink(missing_ok=True)
    executor = ThreadPoolExecutor(
        max_workers=app.config["MAX_WORKERS"], thread_name_prefix="meetnote"
    )
    capacity = app.config["MAX_WORKERS"] + app.config["MAX_PENDING_JOBS"]

    app.extensions["meetnote.jobs"] = repository
    app.extensions["meetnote.executor"] = executor
    app.extensions["meetnote.capacity"] = BoundedSemaphore(capacity)
    app.register_blueprint(web)

    @app.errorhandler(413)
    def request_too_large(_error):
        from flask import jsonify

        return jsonify({"error": "File vượt quá giới hạn dung lượng cho phép."}), 413

    return app
