FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# CCTV feature is parked under `unused functions/cctv`.
# Re-add `ffmpeg` and `nodejs` install before restoring CCTV.

WORKDIR /app

# Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY . .

CMD ["python", "main.py"]