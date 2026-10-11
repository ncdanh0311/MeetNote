"""Gemma audio transcription provider backed by the local Ollama service."""

import base64

import requests


PROMPT = (
    "Hãy nghe đoạn audio này và chuyển toàn bộ nội dung thành văn bản tiếng Việt. "
    "Chỉ trả về transcript. Nếu có nhiều người nói, ghi lời thoại theo thứ tự thời gian."
)


def transcribe_segment(
    segment_path: str,
    base_url: str,
    model: str,
    timeout: int = 300,
) -> str:
    with open(segment_path, "rb") as audio_file:
        audio_data = base64.b64encode(audio_file.read()).decode("ascii")
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": PROMPT, "images": [audio_data]}],
                "stream": False,
                "think": False,
            },
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "Không kết nối được Ollama. Hãy khởi động Ollama và kiểm tra model đã cài."
        ) from error
    except requests.exceptions.Timeout as error:
        raise RuntimeError(
            "Ollama xử lý audio quá lâu. Hãy dùng đoạn ngắn hơn hoặc tăng timeout."
        ) from error
    except requests.exceptions.HTTPError as error:
        if response.status_code == 404:
            raise RuntimeError(
                f"Không tìm thấy model Ollama '{model}'. Hãy pull model này trước khi chạy."
            ) from error
        raise RuntimeError(f"Ollama trả về lỗi HTTP {response.status_code}.") from error

    return response.json().get("message", {}).get("content", "").strip()


def transcribe_segments(
    segment_paths: list[str],
    base_url: str,
    model: str,
    progress_callback=None,
) -> str:
    parts = []
    total = len(segment_paths)
    for index, path in enumerate(segment_paths, start=1):
        parts.append(transcribe_segment(path, base_url=base_url, model=model))
        if progress_callback:
            progress_callback(index, total)
    return "\n".join(parts)
