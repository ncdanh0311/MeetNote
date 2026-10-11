"""Lazy-loaded local Whisper provider with one cached model per configuration."""

import os
from threading import Lock

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import torch
import whisper


_models = {}
_model_lock = Lock()


def get_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def get_model(model_size: str = "medium", device: str | None = None):
    selected_device = device or get_device()
    key = (model_size, selected_device)
    with _model_lock:
        if key not in _models:
            print(
                f"[transcribe] Đang tải Whisper '{model_size}' "
                f"trên thiết bị '{selected_device}'..."
            )
            _models[key] = whisper.load_model(model_size, device=selected_device)
        return _models[key]


def transcribe_segments(
    segment_paths: list[str],
    language: str | None = None,
    model_size: str = "medium",
    device: str | None = None,
    progress_callback=None,
) -> str:
    model = get_model(model_size=model_size, device=device)
    fp16 = model.device.type == "cuda"
    parts = []
    total = len(segment_paths)
    for index, path in enumerate(segment_paths, start=1):
        result = model.transcribe(path, language=language, fp16=fp16)
        parts.append(result.get("text", "").strip())
        if progress_callback:
            progress_callback(index, total)
    return "\n".join(parts)
