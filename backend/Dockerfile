FROM python:3.11-slim

# Best practices for Python in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

# Install dependencies first to leverage layer cache
COPY backend/requirements.txt ./
RUN pip install -U pip && \
    pip install -r requirements.txt

# Copy source code
COPY backend/ ./

# Default command: run the unified entry which starts scheduler and worker
CMD ["python", "-u", "start.py"]

