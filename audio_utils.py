"""
audio_utils.py
--------------
Các hàm xử lý audio: cắt file dài thành nhiều đoạn nhỏ để model AI
xử lý hiệu quả hơn và tránh tràn bộ nhớ với file quá lớn.
"""

import math
import os
from pydub import AudioSegment


def split_audio(audio_path: str, temp_dir: str, segment_minutes: int = 10) -> list[str]:
    """
    Cắt file audio thành nhiều đoạn nhỏ.

    Args:
        audio_path: đường dẫn file audio gốc.
        temp_dir: thư mục để lưu các đoạn đã cắt.
        segment_minutes: độ dài mỗi đoạn (phút).

    Returns:
        Danh sách đường dẫn tới các file đoạn nhỏ, theo đúng thứ tự thời gian.
    """
    # TODO: Tạo thư mục temp_dir nếu chưa tồn tại
    os.makedirs(temp_dir, exist_ok=True)

    audio = AudioSegment.from_file(audio_path)
    segment_ms = segment_minutes * 60 * 1000
    total_ms = len(audio)
    num_segments = math.ceil(total_ms / segment_ms) if total_ms > 0 else 1

    segment_paths = []
    base_name = os.path.splitext(os.path.basename(audio_path))[0]

    for i in range(num_segments):
        start = i * segment_ms
        end = min((i + 1) * segment_ms, total_ms)
        chunk = audio[start:end]

        chunk_path = os.path.join(temp_dir, f"{base_name}_part{i:03d}.wav")
        # Xuất ra wav 16kHz mono — định dạng Whisper xử lý nhanh và ổn định nhất
        chunk = chunk.set_frame_rate(16000).set_channels(1)
        chunk.export(chunk_path, format="wav")
        segment_paths.append(chunk_path)

    return segment_paths

    # pass  # Xoá dòng này khi bắt đầu code


def cleanup_files(paths: list[str]) -> None:
    """Xoá các file tạm sau khi xử lý xong."""
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            pass

