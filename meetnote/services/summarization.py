"""Ollama client for turning transcripts into structured meeting notes."""

import requests


MEETING_MINUTES_PROMPT = """\
Bạn là trợ lý ghi biên bản cuộc họp. Dựa vào nội dung dưới đây, hãy viết biên bản
chuyên nghiệp, súc tích, gồm: tóm tắt chung; nội dung chính; quyết định đã chốt;
việc cần làm tiếp theo và người phụ trách nếu transcript có đề cập.

Nội dung:
---
{transcript}
---

Chỉ trả về biên bản họp, không thêm lời dẫn hay giải thích khác.
"""

PARTIAL_SUMMARY_PROMPT = """\
Tóm tắt phần {part} trên {total} của cuộc họp bằng tiếng Việt. Giữ lại chủ đề,
quyết định, tên người và việc cần làm được nói rõ trong phần này. Không suy đoán.

Nội dung phần này:
---
{content}
---
"""


def _split_text(text: str, limit: int) -> list[str]:
    if limit < 1000:
        raise ValueError("MEETNOTE_SUMMARY_CHUNK_CHARS phải từ 1000 trở lên.")

    remaining = text.strip()
    chunks = []
    while len(remaining) > limit:
        boundaries = [
            position + 1
            for position in (
                remaining.rfind("\n", 0, limit),
                remaining.rfind(". ", 0, limit),
                remaining.rfind("? ", 0, limit),
                remaining.rfind("! ", 0, limit),
            )
            if position >= 0
        ]
        boundary = max(boundaries, default=0)
        if boundary < limit // 2:
            boundary = limit
        chunks.append(remaining[:boundary].strip())
        remaining = remaining[boundary:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def query_ollama(
    prompt: str,
    model: str,
    base_url: str,
    timeout: int = 600,
) -> str:
    url = f"{base_url.rstrip('/')}/api/generate"
    try:
        response = requests.post(
            url,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "Không kết nối được Ollama. Hãy khởi động Ollama và tải model đã cấu hình."
        ) from error
    except requests.exceptions.Timeout as error:
        raise RuntimeError(
            "Ollama xử lý quá lâu. Hãy tăng MEETNOTE_OLLAMA_TIMEOUT hoặc dùng model nhỏ hơn."
        ) from error
    except requests.exceptions.HTTPError as error:
        if response.status_code == 404:
            raise RuntimeError(
                f"Không tìm thấy model Ollama '{model}'. Hãy pull model này trước khi chạy."
            ) from error
        raise RuntimeError(f"Ollama trả về lỗi HTTP {response.status_code}.") from error

    return response.json().get("response", "").strip()


def summarize_transcript(
    transcript: str,
    model: str,
    base_url: str,
    timeout: int = 600,
    chunk_chars: int = 12000,
) -> str:
    if not transcript.strip():
        return "(Không có nội dung transcript để tóm tắt.)"

    chunks = _split_text(transcript, chunk_chars)
    if len(chunks) > 1:
        partial_summaries = [
            query_ollama(
                PARTIAL_SUMMARY_PROMPT.format(
                    part=index, total=len(chunks), content=chunk
                ),
                model=model,
                base_url=base_url,
                timeout=timeout,
            )
            for index, chunk in enumerate(chunks, start=1)
        ]
        transcript = "\n\n".join(partial_summaries)

    return query_ollama(
        MEETING_MINUTES_PROMPT.format(transcript=transcript),
        model=model,
        base_url=base_url,
        timeout=timeout,
    )
