# Use an official Python image as a base
FROM python:3.10-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /build

# apt can appear "stuck" forever on cloud VMs: stuck TCP to mirrors, or broken IPv6. Timeouts +
# retries fail or recover instead of hanging; ForceIPv4 avoids many IPv6-only path issues.
RUN printf '%s\n' \
  'Acquire::http::Timeout "120";' \
  'Acquire::https::Timeout "120";' \
  'Acquire::ftp::Timeout "120";' \
  'Acquire::Retries "5";' \
  'Acquire::ForceIPv4 "true";' \
  > /etc/apt/apt.conf.d/99docker-build

# Compilers only in this stage — needed only if a wheel is missing for your platform during pip install.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Runtime image: no gcc/g++; smaller apt step (often feels “stuck” when ffmpeg + build tools install together)
FROM python:3.10-slim

WORKDIR /usr/src/appdir

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MALLOC_ARENA_MAX=2
ENV MALLOC_MMAP_THRESHOLD_=131072
ENV MALLOC_TRIM_THRESHOLD_=131072
ENV MALLOC_TOP_PAD_=131072
ENV MALLOC_MMAP_MAX_=65536
# Bound V8 heap when yt-dlp invokes Node for JS challenges (image installs nodejs).
ENV NODE_OPTIONS=--max-old-space-size=256

# Same apt robustness as builder (see comment above).
RUN printf '%s\n' \
  'Acquire::http::Timeout "120";' \
  'Acquire::https::Timeout "120";' \
  'Acquire::ftp::Timeout "120";' \
  'Acquire::Retries "5";' \
  'Acquire::ForceIPv4 "true";' \
  > /etc/apt/apt.conf.d/99docker-build

# Runtime OS deps only: ffmpeg (audio/TTS/news/books), nodejs (yt-dlp YouTube JS challenges)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Application code only; .dockerignore excludes .venv/, media, etc. (runtime bind-mounts supply media).
COPY . .
# Safety: never keep a host virtualenv in the image (deps come from /opt/venv above).
RUN rm -rf /usr/src/appdir/.venv /usr/src/appdir/venv /usr/src/appdir/myenv

# Create a non-root user for security and memory efficiency
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /usr/src/appdir

RUN ffmpeg -version && ffprobe -version

USER appuser

# Expose the app port
EXPOSE 5000

# Run Flask on port 5000
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:5000 run:app"]
