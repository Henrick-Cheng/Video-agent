# Video Agent API — slim service image (no GPU, no local inference).
#
# Build:  docker build -t video-agent .
# Run  :  docker run --rm -p 8000:8000 --env-file .env \
#             -v "$PWD/data:/app/data" video-agent
#
# Mock smoke test (no API key needed):
#   curl -X POST localhost:8000/sessions \
#        -H 'Content-Type: application/json' \
#        -d '{"video_path": "data/videos/test1.mp4", "mock": true}'
#
# Notes:
# - Videos come in via the /app/data volume; DASHSCOPE_API_KEY via --env-file.
# - faster-whisper (ASR) is NOT installed to keep the image slim; prepare_l0
#   degrades gracefully to vision-only. `pip install faster-whisper` here if
#   narration transcripts are needed.

FROM python:3.13-slim

WORKDIR /app

COPY requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt

COPY configs/ configs/
COPY src/ src/
COPY main.py .

EXPOSE 8000

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
