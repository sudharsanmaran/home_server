FROM python:3.11-alpine

# Install FFmpeg and dependencies
RUN apk add --no-cache \
    ffmpeg \
    ffmpeg-libs \
    && pip install --no-cache-dir requests

# Create working directory
WORKDIR /app

# Copy scripts
COPY corruption_tracker.py /app/
COPY corruption_analytics.py /app/
COPY convert_mkv_to_mp4.py /app/
COPY radarr_config.json /app/

# Create log directory
RUN mkdir -p /var/log/conversions

# Set environment
ENV PYTHONUNBUFFERED=1

# Keep container running
CMD ["tail", "-f", "/dev/null"]
