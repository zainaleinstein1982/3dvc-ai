import os

FILES = {
    "3dvc/docker-compose.production.yml": """version: "3.9"

services:
  postgres:
    image: postgres:15-alpine
    container_name: 3dvc-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: threedvc
      POSTGRES_PASSWORD: devpassword
      POSTGRES_DB: threedvc_db
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U threedvc"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: 3dvc-redis
    restart: unless-stopped
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: 3dvc-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5

  livekit:
    image: livekit/livekit-server:latest
    container_name: 3dvc-livekit
    restart: unless-stopped
    command: --dev --bind 0.0.0.0 --port 7880
    ports:
      - "7880:7880"
      - "7881:7881"
      - "7882:8080/udp"

  gpu-worker:
    build:
      context: ./backend
      dockerfile: ../docker/gpu-worker.Dockerfile
    container_name: 3dvc-gpu-worker
    restart: unless-stopped
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy

  backend:
    build:
      context: ./backend
      dockerfile: ../docker/backend.Dockerfile
    container_name: 3dvc-backend
    restart: unless-stopped
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/frontend.Dockerfile
    container_name: 3dvc-frontend
    restart: unless-stopped
    ports:
      - "3000:3000"

  caddy:
    image: caddy:2-alpine
    container_name: 3dvc-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - backend
      - frontend

volumes:
  pg_data:
  minio_data:
  caddy_data:
  caddy_config:
""",
    "3dvc/Caddyfile": """{$DOMAIN} {
    handle /api/* {
        reverse_proxy backend:8000 {
            header_up X-Real-IP {remote_host}
        }
    }

    handle /ws/* {
        reverse_proxy livekit:7880
    }

    handle {
        reverse_proxy frontend:3000
    }

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
""",
    "3dvc/.env.example": """DATABASE_URL=postgresql+asyncpg://threedvc:devpassword@localhost:5432/threedvc_db
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=3dvc-ai-assets
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
JWT_SECRET=super-secret-dev-key-change-in-prod
OPENAI_API_KEY=your_openai_key_here
DOMAIN=localhost
""",
    "3dvc/docker/backend.Dockerfile": """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
    "3dvc/docker/frontend.Dockerfile": """FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
USER nextjs
EXPOSE 3000
CMD ["npm", "start"]
""",
    "3dvc/docker/gpu-worker.Dockerfile": """FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN useradd -m appuser
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
USER appuser
CMD ["python3", "scripts/gpu_worker.py"]
"""
}

def create_files():
    for filepath, content in FILES.items():
        full_path = os.path.join(os.getcwd(), filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"Created: {filepath}")

if __name__ == "__main__":
    create_files()
