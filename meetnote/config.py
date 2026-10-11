"""Environment-backed settings for the single-process MeetNote app."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("MEETNOTE_DATA_DIR", BASE_DIR / "instance")).expanduser()


class Config:
    DATA_DIR = DATA_DIR
    UPLOAD_DIR = DATA_DIR / "uploads"
    TEMP_DIR = DATA_DIR / "temp"
    RESULTS_DIR = DATA_DIR / "results"
    DATABASE = Path(os.environ.get("MEETNOTE_DATABASE", DATA_DIR / "meetnote.sqlite3"))

    MAX_CONTENT_LENGTH = int(os.environ.get("MEETNOTE_MAX_UPLOAD_BYTES", str(2 * 1024**3)))
    ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "mp4", "ogg", "flac", "webm"}
    SEGMENT_MINUTES = int(os.environ.get("MEETNOTE_SEGMENT_MINUTES", "10"))
    SUMMARY_CHUNK_CHARS = int(os.environ.get("MEETNOTE_SUMMARY_CHUNK_CHARS", "12000"))
    MAX_WORKERS = max(1, int(os.environ.get("MEETNOTE_MAX_WORKERS", "1")))
    MAX_PENDING_JOBS = max(0, int(os.environ.get("MEETNOTE_MAX_PENDING_JOBS", "2")))

    WHISPER_LANGUAGE = os.environ.get("MEETNOTE_LANGUAGE", "vi") or None
    WHISPER_MODEL = os.environ.get("MEETNOTE_WHISPER_MODEL", "medium")
    WHISPER_DEVICE = os.environ.get("MEETNOTE_WHISPER_DEVICE") or None

    OLLAMA_BASE_URL = os.environ.get("MEETNOTE_OLLAMA_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL = os.environ.get("MEETNOTE_OLLAMA_MODEL", "gemma4:e2b")
    OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("MEETNOTE_OLLAMA_TIMEOUT", "600"))
    FFMPEG_BINARY = os.environ.get("MEETNOTE_FFMPEG", "ffmpeg")

    HOST = os.environ.get("MEETNOTE_HOST", "127.0.0.1")
    PORT = int(os.environ.get("MEETNOTE_PORT", "5001"))
