# GeoLabeler — Architecture Documentation

## Overview

GeoLabeler is a collaborative annotation platform for ESA Destination Earth (DestinE) satellite and climate data. It enables teams of scientists and domain experts to create, review, and export high-quality labels for Sentinel imagery and multidimensional climate simulation datasets (NetCDF, HDF5).

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Browser                           │
│              Single-Page Application (HTML/CSS/JS)              │
│         Canvas Annotation Engine · WebSocket client             │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP / WebSocket
┌───────────────────────────▼─────────────────────────────────────┐
│                     Flask Backend (Python)                       │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Auth Routes  │  │Dataset Routes│  │  Annotation Routes     │ │
│  │ /api/auth/*  │  │/api/datasets/│  │  /api/annotations/*    │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │Image Routes  │  │Dataset Svc   │  │  Annotation Service    │ │
│  │/api/images/* │  │              │  │                        │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
│  ┌─────────────────────┐  ┌──────────────────────────────────┐  │
│  │   AI Service        │  │   Image Service                  │  │
│  │ (sync + async)      │  │ (rasterio, Pillow, netCDF4)      │  │
│  └─────────────────────┘  └──────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Flask-SocketIO                          │  │
│  │      Real-time collaboration (annotation rooms)           │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────┬──────────────────────────┬──────────────────────────┘
           │                          │
┌──────────▼──────┐       ┌───────────▼─────────────────────────┐
│  PostgreSQL 16  │       │   Redis 7                            │
│                 │       │   · Celery broker                    │
│  · Users        │       │   · Celery result backend            │
│  · Datasets     │       │   · SocketIO message queue           │
│  · Images       │       └─────────────────────────────────────┘
│  · Annotations  │
└─────────────────┘       ┌─────────────────────────────────────┐
                          │   Celery Worker(s)                   │
                          │   · AI inference tasks               │
                          │   · Batch AI labeling                │
                          │   · Thumbnail generation             │
                          └─────────────────────────────────────┘
                                       │
                          ┌────────────▼──────────────┐
                          │  External AI Endpoint      │
                          │  (e.g. ONNX, HuggingFace, │
                          │   custom segmentation API) │
                          └───────────────────────────┘
```

---

## Component Descriptions

### Frontend (SPA)
A single-page application served by a minimal Flask process. It communicates with the backend exclusively via the REST API and WebSockets. Key capabilities:
- **Canvas Annotation Engine** (`canvas.js`): HTML5 Canvas-based drawing for bounding boxes, polygons, and point annotations with pan/zoom support.
- **API Client** (`api.js`): Stateless JWT-authenticated fetch wrapper for all REST calls.
- **Real-time collaboration**: WebSocket connection via Socket.IO joins per-image rooms so concurrent annotators see each other's work live.

### Backend (Flask)
The core API server. Responsibilities:
- **Authentication**: JWT (access + refresh tokens) via Flask-JWT-Extended.
- **Dataset management**: CRUD, collaborator management, progress tracking, multi-format export.
- **Image handling**: Upload, metadata extraction (rasterio for GeoTIFF, netCDF4 for .nc, Pillow for standard images), thumbnail generation, locking mechanism.
- **Annotations**: Full CRUD with filtering, bulk creation, review workflow (pending → approved/rejected).
- **WebSockets**: Flask-SocketIO for real-time annotation broadcasting.

### Task Queue (Celery + Redis)
Asynchronous jobs:
| Task | Description |
|------|-------------|
| `run_ai_labeling` | Run AI inference on a single image, persist predictions |
| `run_batch_ai_labeling` | Dispatch per-image tasks for an entire dataset |
| `generate_thumbnails` | Generate JPEG thumbnails for all images in a dataset |

### Database (PostgreSQL)
Four core tables connected by foreign keys:

```
users ─┬──── datasets ──── images ──── annotations
       └─────────────────────────────────↗
             (via annotation.user_id)
```

---

## Data Flow — Annotation Creation

```
User draws bbox on canvas
         │
         ▼
canvas.js captures coordinates
         │
         ▼
POST /api/annotations/image/{id}
         │
         ▼
AnnotationCreateSchema validates payload
         │
         ▼
AnnotationService.create_annotation()
   · Inserts Annotation row
   · Sets Image.is_annotated = True
         │
         ▼
Socket.IO emits "annotation_created"
  to room "image_{id}"
         │
         ▼
All connected clients update their canvas
```

---

## Data Flow — AI-Assisted Labeling

```
User clicks "AI Suggest"
         │
         ▼
POST /api/images/{id}/ai-suggest
         │
         ▼
Celery task run_ai_labeling.delay(image_id)
         │
         ▼
Worker: AIService.predict(image_path)
   · Calls external AI endpoint OR fallback heuristic
   · Returns list of annotation dicts
         │
         ▼
Worker: bulk-inserts Annotation rows (is_ai_generated=True, status="pending")
         │
         ▼
Frontend polls GET /api/images/task/{id}/status
         │
         ▼
On SUCCESS: reload annotations, display AI results for human review
```

---

## Collaborative Editing

Each image has a WebSocket room (`image_{id}`). When a user opens an image for annotation:
1. Frontend emits `join_image_room` → server calls `join_room(f"image_{image_id}")`.
2. Any annotation create/update/delete broadcasts the change to all room members.
3. A soft-lock mechanism (`Image.is_locked`, `Image.locked_by`) prevents two users from annotating the same image simultaneously — the lock is acquired on image open and released on navigation away.

---

## Security

- All endpoints require a valid JWT bearer token (except `/api/auth/login` and `/api/auth/register`).
- Role-based access: `admin` > `reviewer` > `annotator`. Route decorators enforce roles.
- Dataset access is limited to the owner and explicit collaborators.
- File uploads are validated by extension whitelist and stored with UUID filenames to prevent path traversal.

---

## DestinE Integration Points

GeoLabeler is designed to slot into the DestinE platform:
- **Auth**: `DESTINE_AUTH_URL` config allows delegating authentication to the DestinE Keycloak instance (JWT issuer swap).
- **Data ingestion**: Images can be ingested from DestinE STAC catalogs by pointing the upload endpoint to object-store presigned URLs.
- **Export**: GeoJSON export is directly compatible with DestinE's geospatial data fabric; COCO JSON feeds standard ML pipelines.
- **AI endpoint**: `AI_MODEL_ENDPOINT` can point to any DestinE-hosted inference service.

---

## Scalability Considerations

| Concern | Approach |
|---------|----------|
| Large GeoTIFF files (>1 GB) | Streaming upload, rasterio windowed reads for metadata |
| High annotator concurrency | Redis-backed SocketIO message queue, DB connection pooling |
| AI inference latency | Celery async tasks, result polling from frontend |
| Many images per dataset | Paginated APIs (default 20/page), lazy thumbnail generation |
| Multidimensional data (NetCDF) | `time_step` and `band_index` fields on Annotation model |
