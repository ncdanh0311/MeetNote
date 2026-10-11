# MeetNote

Ứng dụng Flask chạy cục bộ để chuyển audio cuộc họp thành transcript và biên bản. Đây là một **modular monolith**: một ứng dụng web duy nhất, với xử lý audio, nhà cung cấp AI và lưu trữ được chia thành các module bên trong.

Dự án gốc: [MiAI MeetNote AI](https://github.com/thangnch/MiAI_MeetNote_Ai) · [Video giới thiệu](https://youtu.be/_52-kz08LvU)

## Yêu cầu

- Python 3.10 trở lên.
- FFmpeg cài trên máy và lệnh `ffmpeg` có trong `PATH`.
- Ollama đang chạy cục bộ và model tóm tắt đã được tải. Mặc định: `gemma4:e2b`.
- Để chọn Whisper, cài các dependency do `openai-whisper` yêu cầu; model Whisper được tải lần đầu sử dụng.

## Cài đặt trên Windows

```powershell
cd D:\Projects\MeetNote
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Cài FFmpeg theo hướng dẫn của nhà cung cấp hệ thống, rồi mở terminal mới và kiểm tra `ffmpeg -version`. Cài Ollama, khởi động ứng dụng Ollama và tải model đã cấu hình, ví dụ `ollama pull gemma4:e2b`.

## Chạy

```powershell
python run.py
```

Mở <http://127.0.0.1:5001>. Có thể dùng `python app.py` để chạy tương thích với cách khởi động cũ.

Mặc định server chỉ bind vào `127.0.0.1`, tắt debug, giới hạn mỗi file 2 GiB và xử lý một job tại một thời điểm. Để đổi cấu hình trong PowerShell:

```powershell
$env:MEETNOTE_PORT = "5001"
$env:MEETNOTE_OLLAMA_URL = "http://127.0.0.1:11434"
$env:MEETNOTE_OLLAMA_MODEL = "gemma4:e2b"
$env:MEETNOTE_WHISPER_MODEL = "medium"
$env:MEETNOTE_LANGUAGE = "vi" # để trống để Whisper tự nhận diện
$env:MEETNOTE_SEGMENT_MINUTES = "10"
$env:MEETNOTE_SUMMARY_CHUNK_CHARS = "12000"
python run.py
```

Các tùy chọn khác: `MEETNOTE_HOST`, `MEETNOTE_DATA_DIR`, `MEETNOTE_MAX_UPLOAD_BYTES`, `MEETNOTE_MAX_WORKERS`, `MEETNOTE_MAX_PENDING_JOBS`, `MEETNOTE_WHISPER_DEVICE`, `MEETNOTE_OLLAMA_TIMEOUT` và `MEETNOTE_FFMPEG`. Chỉ đổi `MEETNOTE_HOST` sang địa chỉ mạng khi bạn hiểu rằng ứng dụng hiện chưa có đăng nhập và chỉ nên dùng trong mạng tin cậy.

## Lưu trữ và xử lý

SQLite giữ trạng thái job và đường dẫn kết quả trong `instance/meetnote.sqlite3`; audio tải lên, đoạn tạm và kết quả nằm trong các thư mục con của `instance/`. Kết quả hoàn tất vẫn tải lại được sau khi khởi động lại server. Job đang xử lý khi server dừng sẽ được đánh dấu lỗi và cần tải file lên lại. File audio gốc và các đoạn tạm được xóa sau khi xử lý kết thúc.

Whisper được tải lười khi có job đầu tiên chọn Whisper và tái sử dụng trong tiến trình. FFmpeg chia file theo luồng, chuyển các đoạn sang WAV mono 16 kHz để không phải nạp toàn bộ audio vào RAM. Transcript dài được tóm tắt theo nhiều phần trước khi hợp nhất. Biên bản hiển thị dưới dạng văn bản; nội dung model không được diễn giải thành HTML.

Trang chủ hiển thị tối đa 20 job gần nhất cùng liên kết tải biên bản Markdown và transcript văn bản. Có thể kiểm tra server tại `/health`; API trạng thái hiện tại là `/status/<job_id>`.

## Cấu trúc

```text
run.py
app.py                       # entrypoint tương thích
meetnote/
  config.py
  web.py                      # routes HTTP
  services/
    audio.py
    pipeline.py
    summarization.py
    transcription/
      whisper.py
      gemma.py
  storage/
    jobs.py
    results.py
  templates/index.html
  static/css/app.css
  static/js/app.js
```
