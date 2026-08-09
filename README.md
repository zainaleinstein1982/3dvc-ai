# 3DVC AI

Spatial video conferencing platform with real-time AI-driven 3D avatars, edge face tracking, and spatial audio.

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11), SQLAlchemy (async), Alembic |
| Database | PostgreSQL 15 |
| Cache / Queue | Redis 7 |
| Object Storage | MinIO |
| Real-time media (SFU) | LiveKit |
| Frontend | Next.js 14, React 18, TypeScript |
| 3D Rendering | Three.js, React Three Fiber, Drei |
| Face Tracking | MediaPipe Tasks Vision (WASM, runs in a Web Worker) |
| Reverse Proxy / TLS | Caddy |
| Containerization | Docker, Docker Compose |

## Project Structure

```
.
├── backend/                # FastAPI application
│   ├── app/
│   │   ├── ai/              # GPU job queue, face/depth model wrappers
│   │   ├── api/              # REST routers (auth, rooms, ai, sfu, health)
│   │   ├── auth/              # JWT + password hashing
│   │   ├── db/                 # SQLAlchemy models & session
│   │   ├── observability/       # Metrics + circuit breaker
│   │   └── storage/               # MinIO client wrapper
│   ├── scripts/gpu_worker.py    # Standalone GPU worker process
│   ├── main.py
│   └── requirements.txt
├── frontend/                # Next.js application
│   └── src/
│       ├── app/               # App router pages
│       ├── components/         # Room, Avatar3D, Login, Diagnostics
│       ├── lib/                  # WebRTC, audio, rendering, tracking helpers
│       └── workers/               # Face tracking Web Worker
├── docker/                  # Dockerfiles (backend, frontend, gpu-worker)
├── alembic/                 # Database migrations
├── scripts/                 # Postgres backup/restore shell scripts
├── docs/                    # Architecture diagrams, demo script, checklists
├── scripts_generator/       # Original Python generator scripts (build_part1-10.py)
├── docker-compose.production.yml
├── Caddyfile
└── .env.example
```

> **Note:** The `scripts_generator/` folder contains the original `build_partN.py` scripts used to scaffold this repository. They are kept for reference/reproducibility and are **not** needed to run the application — you can delete this folder safely once the repo is set up.

## Getting Started (Local Development with Docker)

### 1. Prerequisites

- Docker & Docker Compose
- (Optional, for GPU inference) NVIDIA GPU + [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:
- `JWT_SECRET` — a strong random string
- `OPENAI_API_KEY` — if you use the AI mediation features
- `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` — matching your LiveKit server config

### 3. Run the stack

```bash
docker compose -f docker-compose.production.yml up --build
```

This starts: PostgreSQL, Redis, MinIO, LiveKit, the FastAPI backend, the GPU worker, the Next.js frontend, and Caddy as reverse proxy.

- Frontend: http://localhost:3000 (or http://localhost via Caddy)
- Backend API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001

### 4. Default admin login

An admin user is seeded automatically on first backend startup:

```
email:    admin@3dvc.ai
password: admin123
```

**Change this immediately in any non-local environment.**

### 5. Database migrations

Migrations run via Alembic. To apply them manually:

```bash
cd backend
alembic upgrade head
```

## Running Without Docker (manual dev setup)

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

You'll still need PostgreSQL, Redis, MinIO, and LiveKit running somewhere (locally via Docker or remote) and referenced correctly in `.env`.

## Deploying to GitHub

```bash
git init
git add .
git commit -m "Initial commit: 3DVC AI platform"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

> `.env` is excluded via `.gitignore` — never commit real secrets. Only `.env.example` (with placeholder values) is tracked.

## Production Deployment

See [`docs/PRODUCTION-CHECKLIST.md`](docs/PRODUCTION-CHECKLIST.md) before deploying to a live environment, and [`docs/ARCHITECTURE-DIAGRAM.md`](docs/ARCHITECTURE-DIAGRAM.md) for system diagrams.

## Documentation

- [Architecture Diagrams](docs/ARCHITECTURE-DIAGRAM.md)
- [Demo Script](docs/DEMO-SCRIPT.md)
- [Production Checklist](docs/PRODUCTION-CHECKLIST.md)
- [Verification Reports](docs/M30-VERIFICATION-REPORT.md)

## License

Add your license of choice here (e.g. MIT, Apache-2.0) before making the repository public.
