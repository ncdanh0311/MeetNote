"""Split uploaded media with FFmpeg without loading the complete file into RAM."""

import subprocess
from pathlib import Path


def split_audio(
    audio_path: str | Path,
    temp_dir: str | Path,
    segment_minutes: int = 10,
    ffmpeg_binary: str = "ffmpeg",
) -> list[str]:
    if segment_minutes < 1:
        raise ValueError("Độ dài mỗi đoạn phải ít nhất 1 phút.")

    destination = Path(temp_dir)
    destination.mkdir(parents=True, exist_ok=True)
    pattern = destination / "part_%03d.wav"
    command = [
        ffmpeg_binary,
        "-hide_banner",
        "-nostdin",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        "-f",
        "segment",
        "-segment_time",
        str(segment_minutes * 60),
        "-reset_timestamps",
        "1",
        str(pattern),
    ]

    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as error:
        raise RuntimeError(
            "Không tìm thấy FFmpeg. Hãy cài FFmpeg và thêm ffmpeg vào PATH."
        ) from error

    if completed.returncode:
        detail = completed.stderr.strip().splitlines()
        reason = detail[-1] if detail else "không rõ nguyên nhân"
        raise RuntimeError(f"FFmpeg không đọc được file audio: {reason}")

    segments = sorted(destination.glob("part_*.wav"))
    if not segments:
        raise RuntimeError("File không có dữ liệu audio để xử lý.")
    return [str(path) for path in segments]


def cleanup_files(paths: list[str]) -> None:
    for path in paths:
        try:
            Path(path).unlink()
        except OSError:
            pass
