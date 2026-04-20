# GeoLabeler — API Design Reference

Base URL: `http://localhost:5000/api`

All endpoints except authentication require:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## Authentication

### POST /auth/register
Create a new user account.

**Request body:**
```json
{
  "username": "scientist1",
  "email": "scientist@esa.int",
  "password": "secure_password",
  "full_name": "Dr. Jane Smith",
  "role": "annotator"          // annotator | reviewer | admin
}
```
**Response 201:**
```json
{
  "user": { "id": 1, "username": "scientist1", "role": "annotator", ... },
  "access_token": "<jwt>",
  "refresh_token": "<jwt>"
}
```

---

### POST /auth/login
```json
{ "username": "scientist1", "password": "secure_password" }
```
**Response 200:** same as register.

---

### POST /auth/refresh
Requires `Authorization: Bearer <refresh_token>`.
**Response 200:** `{ "access_token": "<new_jwt>" }`

---

### DELETE /auth/logout
Revokes the current access token.
**Response 200:** `{ "message": "Successfully logged out" }`

---

### GET /auth/me
Returns the authenticated user profile.

### PUT /auth/me
Update `full_name`, `email`, or `password`.

---

## Datasets

### GET /datasets/
List datasets accessible to the authenticated user (owned + collaborator).

**Query parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default: 1) |
| `per_page` | int | Items per page (default: 20, max: 100) |
| `search` | string | Name search (partial match) |
| `data_type` | string | Filter by type |
| `status` | string | active \| completed \| archived |

**Response 200:**
```json
{
  "items": [{ "id": 1, "name": "Sentinel-2 Europe", "completion_percentage": 42.5, ... }],
  "total": 15,
  "pages": 1,
  "current_page": 1,
  "per_page": 20
}
```

---

### POST /datasets/
Create a new dataset.

**Request body:**
```json
{
  "name": "Sentinel-2 Alps 2024",
  "description": "High-alpine imagery, 10m resolution",
  "data_type": "sentinel_optical",
  "label_schema": {
    "classes": [
      { "id": "snow", "name": "Snow/Ice", "color": "#d0eeff" },
      { "id": "rock", "name": "Rock",     "color": "#a08060" }
    ],
    "annotation_types": ["bbox", "polygon"],
    "allow_multiple_labels": false
  },
  "metadata": { "bands": ["B02","B03","B04","B08"], "resolution_m": 10 }
}
```

`data_type` options: `sentinel_optical` | `sentinel_sar` | `sentinel_radar` | `climate_simulation` | `dem` | `multispectral` | `hyperspectral` | `other`

---

### GET /datasets/{id}
Returns dataset detail including stats (`image_count`, `annotation_count`, `completion_percentage`).

### PUT /datasets/{id}
Update dataset fields. Owner or admin only.

### DELETE /datasets/{id}
Delete dataset and all associated images/annotations. Owner or admin only.

---

### GET /datasets/{id}/stats
```json
{
  "total_images": 200,
  "annotated_images": 84,
  "completion_percentage": 42.0,
  "total_annotations": 1340,
  "label_distribution": { "cloud": 480, "water": 320, "urban": 540 },
  "type_distribution":  { "bbox": 900, "polygon": 440 },
  "status_distribution": { "pending": 800, "approved": 540 }
}
```

---

### GET /datasets/{id}/export
Export annotations.

**Query params:** `format=coco|geojson|csv`

- **COCO JSON**: Standard COCO object detection format with categories derived from label schema.
- **GeoJSON**: FeatureCollection with each annotation as a Feature, image bbox in properties.
- **CSV**: Tabular rows with image_id, filename, label, geometry.

---

### POST /datasets/{id}/collaborators
Add a collaborator by email. Owner only.
```json
{ "email": "colleague@esa.int" }
```

### DELETE /datasets/{id}/collaborators/{user_id}
Remove collaborator. Owner only.

---

## Images

### GET /images/dataset/{dataset_id}
List images in a dataset (paginated).

**Query params:** `page`, `per_page`, `is_annotated=true|false`

---

### POST /images/dataset/{dataset_id}/upload
Upload one or more image files (multipart/form-data).

**Form fields:** `file` (repeatable)

**Supported formats:** `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.nc`, `.h5`, `.hdf5`

**Response 201:**
```json
{
  "uploaded": [{ "id": 5, "filename": "abc123.tif", "width": 10980, "bands": 4, ... }],
  "errors":   [{ "filename": "bad.pdf", "error": "File type not allowed" }]
}
```

---

### GET /images/{id}
Returns image metadata. Add `?include_annotations=true` for embedded annotations.

### DELETE /images/{id}
Delete image file and record. Owner or admin only.

### GET /images/{id}/file
Stream the raw image file.

### GET /images/{id}/thumbnail
Stream a 256×256 JPEG thumbnail.

---

### POST /images/{id}/lock
Acquire a soft lock on an image (exclusive annotation).
Fails with 409 if locked by another user.

### POST /images/{id}/unlock
Release the lock. Lock holder or admin only.

---

### POST /images/{id}/ai-suggest
Queue an AI inference task for the image.

**Response 202:**
```json
{ "task_id": "abc123def456", "message": "AI labeling task queued" }
```

### GET /images/task/{task_id}/status
Poll AI task status.
```json
{ "task_id": "...", "status": "SUCCESS|PENDING|FAILURE", "result": { ... } }
```

---

## Annotations

### GET /annotations/image/{image_id}
List annotations for an image.

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Default 1 |
| `per_page` | int | Default 50, max 200 |
| `label` | string | Exact label match |
| `annotation_type` | string | bbox \| polygon \| point \| … |
| `status` | string | pending \| approved \| rejected \| needs_review |
| `is_ai_generated` | bool | true \| false |
| `user_id` | int | Filter by annotator |

---

### POST /annotations/image/{image_id}
Create a single annotation.

**Request body:**
```json
{
  "annotation_type": "bbox",
  "label": "cloud",
  "label_id": "cloud",
  "confidence": 0.95,
  "geometry": {
    "type": "bbox",
    "coordinates": [120, 80, 340, 260]
  },
  "attributes": { "cloud_type": "cumulus", "opacity": 0.8 },
  "band_specific": false,
  "band_index": null,
  "time_step": null
}
```

**Geometry formats by type:**

| Type | Geometry |
|------|---------|
| `bbox` | `{"type":"bbox","coordinates":[x1,y1,x2,y2]}` |
| `polygon` | `{"type":"Polygon","coordinates":[[[lon,lat],...]]}` |
| `point` | `{"type":"Point","coordinates":[x,y]}` |
| `polyline` | `{"type":"LineString","coordinates":[[x,y],...]}` |
| `classification` | `{"type":"classification","coordinates":[]}` |
| `segmentation_mask` | `{"type":"mask","rle":{"counts":...,"size":[h,w]}}` |

---

### POST /annotations/image/{image_id}/bulk
Create multiple annotations in a single transaction.
```json
{
  "annotations": [ { ...annotation... }, { ...annotation... } ]
}
```
**Response 201:** Array of created annotation objects.

---

### GET /annotations/{id}
Get a single annotation.

### PUT /annotations/{id}
Update an annotation. Author, reviewer, or admin only.
Updatable fields: `label`, `confidence`, `geometry`, `attributes`, `status`, `review_comment`.

### DELETE /annotations/{id}
Delete an annotation. Author, reviewer, or admin only.

---

### POST /annotations/{id}/review
Set review status. Requires `reviewer` or `admin` role.
```json
{
  "status": "approved",
  "comment": "Well-delineated cloud boundary"
}
```
`status` options: `approved` | `rejected` | `needs_review`

---

## WebSocket Events

Connect to `ws://localhost:5000` using Socket.IO.

### Client → Server

| Event | Payload | Description |
|-------|---------|-------------|
| `join_image_room` | `{"image_id": 42}` | Subscribe to annotation updates for an image |
| `leave_image_room` | `{"image_id": 42}` | Unsubscribe |

### Server → Client

| Event | Payload | Description |
|-------|---------|-------------|
| `annotation_created` | `{"image_id":42,"annotation":{...}}` | New annotation |
| `annotation_updated` | `{"image_id":42,"annotation":{...}}` | Annotation modified |
| `annotation_deleted` | `{"image_id":42,"annotation_id":7}` | Annotation removed |
| `annotations_bulk_created` | `{"image_id":42,"count":5}` | Bulk insert complete |

---

## Error Responses

All errors follow:
```json
{ "error": "Human-readable message" }
```

| Code | Meaning |
|------|---------|
| 400 | Validation error (see `error` for field details) |
| 401 | Missing or invalid JWT |
| 403 | Insufficient role/ownership |
| 404 | Resource not found |
| 409 | Conflict (duplicate username, locked image) |
| 422 | Unprocessable entity |
| 500 | Internal server error |
