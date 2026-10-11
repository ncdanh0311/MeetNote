"""Background orchestration for one meeting-note job."""

import logging
import shutil
from pathlib import Path

from .audio import cleanup_files, split_audio
from ..storage.results import write_result


logger = logging.getLogger(__name__)


def process_job(job_id: str, upload_path: str, engine: str, repository, settings: dict) -> None:
    segment_dir = Path(settings["TEMP_DIR"]) / job_id
    segment_paths: list[str] = []
    try:
        repository.update(job_id, status="splitting", message="Đang chia nhỏ file audio...")
        segment_paths = split_audio(
            upload_path,
            segment_dir,
            segment_minutes=settings["SEGMENT_MINUTES"],
            ffmpeg_binary=settings["FFMPEG_BINARY"],
        )

        label = "Whisper" if engine == "whisper" else "Gemma"
        total = len(segment_paths)
        repository.update(
            job_id,
            status="transcribing",
            message=f"Đang chuyển giọng nói bằng {label} (0/{total})...",
        )

        def report_progress(current: int, count: int) -> None:
            repository.update(
                job_id,
                message=f"Đang chuyển giọng nói bằng {label} ({current}/{count})...",
            )

        if engine == "whisper":
            from .transcription.whisper import transcribe_segments

            transcript = transcribe_segments(
                segment_paths,
                language=settings["WHISPER_LANGUAGE"],
                model_size=settings["WHISPER_MODEL"],
                device=settings["WHISPER_DEVICE"],
                progress_callback=report_progress,
            )
        else:
            from .transcription.gemma import transcribe_segments

            transcript = transcribe_segments(
                segment_paths,
                base_url=settings["OLLAMA_BASE_URL"],
                model=settings["OLLAMA_MODEL"],
                progress_callback=report_progress,
            )

        repository.update(
            job_id, status="summarizing", message="Đang tóm tắt thành biên bản họp..."
        )
        from .summarization import summarize_transcript

        minutes = summarize_transcript(
            transcript,
            model=settings["OLLAMA_MODEL"],
            base_url=settings["OLLAMA_BASE_URL"],
            timeout=settings["OLLAMA_TIMEOUT_SECONDS"],
            chunk_chars=settings["SUMMARY_CHUNK_CHARS"],
        )
        result_path = write_result(settings["RESULTS_DIR"], job_id, minutes, transcript)
        repository.update(
            job_id,
            status="completed",
            message="Hoàn tất!",
            result_path=str(result_path),
        )
    except Exception as error:
        logger.exception("Job %s failed", job_id)
        try:
            repository.update(job_id, status="error", message=f"Lỗi xử lý: {error}")
        except Exception:
            logger.exception("Could not record failure for job %s", job_id)
    finally:
        cleanup_files(segment_paths)
        shutil.rmtree(segment_dir, ignore_errors=True)
        try:
            Path(upload_path).unlink()
        except OSError:
            pass
