FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN useradd -m appuser
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
USER appuser
CMD ["python3", "scripts/gpu_worker.py"]
