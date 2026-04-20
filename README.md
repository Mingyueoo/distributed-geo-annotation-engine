# GeoLabeler

GeoLabeler is a collaborative annotation platform for satellite and climate data.
![Product Demo](docs/label.gif)

## Features

- **Multi-format data support** — Sentinel-2 optical (GeoTIFF, multispectral), Sentinel-1 SAR, NetCDF climate simulation data, HDF5, standard imagery
- **Full annotation toolset** — bounding boxes, polygons, points, polylines, whole-image classification, segmentation masks
- **Collaborative real-time editing** — WebSocket rooms per image; changes propagate instantly to all annotators
- **Review workflow** — pending → approved / rejected / needs_review with reviewer comments
- **AI-assisted labeling** — pluggable external inference endpoint; async Celery tasks with frontend polling
- **Multi-format export** — COCO JSON, GeoJSON, CSV
- **Role-based access control** — admin, reviewer, annotator
- **DestinE-aligned architecture** — JWT auth delegation, STAC-compatible ingest, GeoJSON output

---

## Tech Stack

- **Backend**: Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-SocketIO
- **Database**: PostgreSQL
- **Queue**: Celery + Redis
- **Frontend**: Flask (serving static SPA)
- **Containerization**: Docker Compose

---


## Quick Start (Docker Compose)

### Prerequisites
- Docker 24+ and Docker Compose v2
- (Optional) An external AI inference endpoint

### 1. Clone and configure
```bash
git clone https://github.com/Mingyueoo/distributed-geo-annotation-engine.git
cd distributed-geo-annotation-engine
cp .env          # edit secrets as needed
```

### 2. Start all services
```bash
docker compose up --build
```

This starts:
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:5000 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| Celery worker | (background) |

### 3. Seed the database
```bash
docker compose exec backend python scripts/seed_data.py
```

Default accounts created:
| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | admin |
| `annotator1` | `pass1234` | annotator |
| `reviewer1` | `pass1234` | reviewer |

### 4. Open the app
Navigate to **http://localhost:3000** and sign in.

---

## Local Development (without Docker)

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start PostgreSQL and Redis (e.g. via Docker or Homebrew)
docker run -d -p 5432:5432 -e POSTGRES_USER=geolabeler -e POSTGRES_PASSWORD=password -e POSTGRES_DB=geolabeler postgres:16-alpine
docker run -d -p 6379:6379 redis:7-alpine

# Apply DB migrations
flask db upgrade

# Run the API server
python -m app.main

# In a separate terminal, run the Celery worker
celery -A worker.celery worker --loglevel=info
```

### Frontend
```bash
cd frontend
pip install flask python-dotenv
python app.py
```

---

## Running Tests

```bash
cd geo-labeler
pip install pytest pytest-flask

# All tests
pytest tests/ -v

# API tests only
pytest tests/test_api.py -v

# Service unit tests only
pytest tests/test_services.py -v

# With coverage
pytest tests/ --cov=backend/app --cov-report=term-missing
```

---

## Project Structure

```
geo-labeler/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # App factory
│   │   ├── config.py            # Environment-based configuration
│   │   ├── extensions.py        # Flask extensions (db, jwt, socketio, celery)
│   │   ├── models/
│   │   │   ├── user.py          # User accounts with role-based access
│   │   │   ├── dataset.py       # Datasets with label schema and collaborators
│   │   │   ├── image.py         # Images with geospatial metadata
│   │   │   └── annotation.py    # Annotations with geometry, review state
│   │   ├── schemas/
│   │   │   ├── dataset_schema.py
│   │   │   └── annotation_schema.py
│   │   ├── routes/
│   │   │   ├── auth_routes.py
│   │   │   ├── dataset_routes.py
│   │   │   ├── image_routes.py
│   │   │   └── annotation_routes.py
│   │   ├── services/
│   │   │   ├── dataset_service.py   # Business logic, export
│   │   │   ├── annotation_service.py
│   │   │   ├── image_service.py     # Upload, metadata extraction, thumbnails
│   │   │   └── ai_service.py        # AI endpoint integration + fallback
│   │   ├── tasks/
│   │   │   └── ai_tasks.py          # Celery async AI labeling
│   │   └── utils/
│   │       ├── auth_utils.py
│   │       └── file_utils.py
|   ├── scripts/
│   |   ├── init_db.py
│   |   └── seed_data.py 
│   ├── worker.py                # Celery worker entrypoint
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── templates/index.html     # Single-page application shell
│   ├── static/
│   │   ├── css/main.css         # Full design system
│   │   └── js/
│   │       ├── api.js           # REST API client
│   │       ├── canvas.js        # HTML5 Canvas annotation engine
│   │       └── app.js           # SPA controller
│   └── app.py
├── tests/
│   ├── test_api.py              # Integration tests
│   └── test_services.py        # Unit tests
├── docs/
│   ├── architecture.md
│   └── api_design.md
├── docker-compose.yml
├── .env
└── README.md
```

---

## Configuration Reference

All settings are read from environment variables (or `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | — | Flask secret key |
| `JWT_SECRET_KEY` | — | JWT signing key |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL (Celery + SocketIO) |
| `UPLOAD_FOLDER` | `/tmp/geo-labeler/uploads` | File storage root |
| `AI_MODEL_ENDPOINT` | `""` | External AI inference URL |
| `AI_API_KEY` | `""` | Bearer token for AI endpoint |
| `DESTINE_API_URL` | — | DestinE platform API |
| `DESTINE_AUTH_URL` | — | DestinE Keycloak URL |

---

## AI Integration

GeoLabeler supports pluggable AI inference:

1. **Set `AI_MODEL_ENDPOINT`** to your inference server URL.
2. The server must accept `POST /predict` with a multipart `image` field and return one of:
   - `{"predictions": [{"type":"bbox","label":"cloud","score":0.9,"geometry":{...}}]}`
   - `{"boxes": [{"bbox":[x1,y1,x2,y2],"class":"water","score":0.75}]}`
3. When no endpoint is configured, a fallback heuristic is used (returns a low-confidence placeholder).
4. AI-generated annotations are flagged (`is_ai_generated: true`, `status: "pending"`) and must be human-reviewed before export.

---

## Export Formats

| Format | Use Case |
|--------|----------|
| **COCO JSON** | Training object detection models (YOLO, Detectron2, MMDetection) |
| **GeoJSON** | GIS tools, DestinE geospatial data fabric, QGIS |
| **CSV** | Spreadsheet analysis, custom ML pipelines |

Only `approved` annotations are included in exports.

---

## DestinE Integration

GeoLabeler aligns with the DestinE platform architecture:

- **Authentication**: JWT issuer can be swapped to point at the DestinE Keycloak instance by updating `DESTINE_AUTH_URL`.
- **Data ingestion**: Images can be ingested directly from DestinE STAC endpoints or object storage by uploading via presigned URLs.
- **Output**: GeoJSON export is compatible with DestinE's geospatial data layer. Label schemas map to DestinE taxonomy concepts.
- **Deployment**: Docker Compose configuration is compatible with DestinE's Kubernetes-based infrastructure (convert with `kompose convert`).


---



