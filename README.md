# PondPlan — Pond Catchment Analysis API

A FastAPI backend that turns a raw contour map into an actionable pond-siting recommendation. Upload a **KML/KMZ** contour file, optionally draw a land boundary, and the API builds a terrain elevation model, finds the best pond location, delineates its catchment, and estimates how much water it can realistically store — with no hardcoded coordinates, so it generalizes to any contour map.

Built for automated rural/village water-conservation planning as part of the **PondPlan** system (paired with a [React + Leaflet frontend](https://github.com/sunilkumar2170/frontted-api)).

---

## Table of contents

- [Overview](#overview)
- [How it works](#how-it-works)
- [API reference](#api-reference)
  - [POST /analyzeContour](#post-analyzecontour)
  - [GET / and GET /analyzeContour](#get--and-get-analyzecontour)
- [Architectural approach & hydrological modeling](#architectural-approach--hydrological-modeling)
- [Project structure](#project-structure)
- [Running locally](#running-locally)
- [Deployment](#deployment)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Author](#author)

---

## Overview

| | |
|---|---|
| **Input** | A KML/KMZ contour map, plus an optional user-drawn land boundary |
| **Output** | Pond coordinates, elevation, catchment polygon, rainfall, runoff depth, expected water volume |
| **Stack** | Python 3.12 · FastAPI · Uvicorn · NumPy · SciPy · Shapely · HTTPX |
| **Deployment** | Linux server, `uvicorn` under `tmux`, exposed on `10.1.75.53:3213` |

The pipeline is fully data-driven — every result is derived from the uploaded contour geometry (and, when provided, the user's drawn boundary). Nothing about a specific site is ever hardcoded, so the same code works on any valid contour map.

## How it works

```
KML/KMZ file  ──┐
                 ├──▶  Parse & filter  ──▶  Elevation grid (DEM)  ──▶  Pond site (local minimum)
Land boundary ──┘                                                          │
  (optional)                                                               ▼
                                                              D8 flow direction ──▶ BFS catchment
                                                                                        │
                                                                                        ▼
                                                        Rainfall lookup ──▶ SCS-CN runoff ──▶ Water volume
```

1. **Parse** the contour map into `(lon, lat, elevation)` points.
2. If a **land boundary** was drawn on the frontend, keep only the points that fall inside it (`shapely.Polygon.contains`) — this is what lets the analysis be restricted to a user-selected parcel instead of the whole file.
3. **Interpolate** those points into a regular elevation grid.
4. Find the **lowest point** in the grid as the candidate pond site.
5. Trace **D8 flow directions** and run a **BFS** upstream from the pond site to find every cell that drains into it — that's the catchment.
6. Look up **rainfall** for the pond's coordinates, apply the **SCS Curve Number** method to get runoff depth, and multiply by catchment area to get expected water volume.

## API reference

### `POST /analyzeContour`
Alias: `POST /findCatchment`

**Content type:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `contour_map` | file | ✅ | KML or KMZ contour map |
| `file` | file | — | Alternative field name, accepted as a fallback |
| `land_area` | string (JSON) | — | Optional `[[lon, lat], [lon, lat], ...]` polygon. When present, only contour points inside this boundary are analyzed. |

**Request example**

```bash
curl -X POST "http://10.1.75.53:3213/analyzeContour" \
  -F "contour_map=@contours_1m.kml" \
  -F 'land_area=[[81.2879,21.2497],[81.2921,21.2497],[81.2921,21.2530],[81.2879,21.2530]]'
```

**Response example** (`application/json`)

```json
{
  "filename": "contours_1m.kml",
  "pond_location": {
    "longitude": 81.28897840326482,
    "latitude": 21.24486206234389
  },
  "pond_elevation_m": 268.0,
  "catchment_area_hectares": 4.261316548620606,
  "total_catchment_cells": 49,
  "catchment_polygon": [
    [81.28913619301537, 21.243782143985634],
    [81.28913619301537, 21.244022125843024]
  ],
  "rainfall_used_mm": 1382.66,
  "curve_number_used": 60.0,
  "runoff_depth_mm": 1198.3476056309169,
  "expected_water_volume_cubic_m": 51065.384828749055
}
```

**Response fields**

| Field | Description |
|---|---|
| `pond_location` | Recommended pond coordinates — the lowest natural depression in the (optionally boundary-filtered) terrain |
| `pond_elevation_m` | Elevation of the recommended pond site, in metres |
| `catchment_area_hectares` | Total area contributing surface runoff to the pond site |
| `total_catchment_cells` | Number of DEM grid cells included in the catchment |
| `catchment_polygon` | Catchment boundary as `[longitude, latitude]` points — ready for direct map overlay (Leaflet, GeoJSON-style) |
| `rainfall_used_mm` | Annual rainfall used in the runoff calculation, fetched live for the pond's coordinates |
| `curve_number_used` | SCS Curve Number applied (reflects soil/land-use infiltration characteristics) |
| `runoff_depth_mm` | Estimated runoff depth from the SCS-CN method |
| `expected_water_volume_cubic_m` | Estimated total water volume the catchment can be expected to yield annually |

**Error responses**

| Status | Meaning |
|---|---|
| `400` / `422` | File missing, unreadable, or an invalid/malformed `land_area` polygon |
| `422` | `land_area` boundary too small — fewer than 3 contour points fall inside it |
| `500` | Unexpected server-side failure during terrain processing |

### `GET /` and `GET /analyzeContour`
Lightweight status routes — return server status and available endpoints. `GET /analyzeContour` exists specifically so opening the analysis URL directly in a browser (instead of `POST`-ing to it) returns a friendly message rather than a `405`.

---

## Architectural approach & hydrological modeling

1. **KML / KMZ ingestion & parsing** (`kml_parser.py`)
   Supports both uncompressed `.kml` and compressed `.kmz` archives. Extracts elevation robustly from `<name>`, `<ExtendedData>`, `<description>`, or 3D coordinate tuples `(lon, lat, elev)`. No hardcoded geography — generalizes to any valid contour map.

2. **Optional boundary filtering** (`main.py`)
   When the frontend sends a `land_area` polygon, contour points are filtered to that boundary with `shapely.Polygon.contains` *before* any terrain processing — so every downstream step operates only on the user-selected parcel.

3. **Surface interpolation & pseudo-DEM** (`terrain_processor.py`)
   Flattens scattered contour vertices into `(x, y, z)` points and interpolates a regular elevation grid with SciPy's 2D linear barycentric interpolation (`scipy.interpolate.griddata`). Grid arrays are downcast to `float32` and kept at a balanced 70×70 resolution to stay memory-safe under load.

4. **Optimal pond site selection** (`catchment_analyzer.py`)
   An 8-neighborhood local-minimum detector locates natural terrain depressions; the deepest viable one becomes the pond outlet.

5. **D8 flow direction & catchment delineation** (`catchment_analyzer.py`)
   Steepest-descent flow vectors are computed for every DEM cell (standard D8 model), then a reverse BFS from the pond sink traces every upstream cell that drains into it.

6. **Geodesic catchment area estimation** (`catchment_analyzer.py`)
   Cell dimensions are computed in metres with latitude-corrected geodesic scaling (1° lat ≈ 111 km; 1° lon ≈ 111 km × cos(latitude)), then summed to a hectare figure.

7. **Catchment boundary polygon** (`catchment_analyzer.py`)
   Each contributing cell becomes a small square polygon; `shapely.unary_union` merges them into one catchment boundary, returned as an ordered `[longitude, latitude]` ring for direct map overlay.

8. **Live rainfall retrieval** (`rainfall_service.py`)
   Fetches the past year's rainfall for the pond's exact coordinates from the **Open-Meteo Historical Weather API**, falling back to **NASA POWER** if the primary source is unavailable or rate-limited, and to a fixed default only if both fail — so the pipeline never breaks on a network issue. Results are cached in memory per location.

9. **Runoff & water volume estimation** (`catchment_analyzer.py`)
   Applies the **SCS Curve Number (CN)** method:

   ```
   S = (25400 / CN) − 254        # potential maximum retention, mm
   Q = (P − 0.2S)² / (P + 0.8S)  # runoff depth, mm   (for P > 0.2S)
   V = (Q / 1000) × (A × 10000)  # expected water volume, m³
   ```

---

## Project structure

```
pond-catchment-api/
├── main.py                 # FastAPI app, route handlers, land_area filtering, request orchestration
├── kml_parser.py            # KML & KMZ parser with robust elevation extraction
├── terrain_processor.py     # Grid interpolation & DEM construction (float32, 70x70)
├── catchment_analyzer.py    # Local minima detection, D8 flow routing, BFS catchment tracing,
│                             # catchment polygon generation, and SCS-CN water volume estimation
├── rainfall_service.py      # Live rainfall retrieval (Open-Meteo + NASA POWER fallback, cached)
├── models.py                # Pydantic response models
├── requirements.txt         # Dependencies
├── contours_1m.kml          # Sample contour map for testing
└── README.md                # This file
```

## Running locally

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Interactive Swagger docs: `http://localhost:8000/docs`

## Deployment

The API is deployed on a shared Linux lab server and kept alive with `tmux` so it survives SSH disconnects:

```bash
ssh -p 2213 student@10.1.75.53
cd pond-catchment-api
source venv/bin/activate
tmux new -s pond_backend
uvicorn main:app --host 0.0.0.0 --port 3213
# Ctrl+B, D to detach — the server keeps running after you disconnect
```

| | |
|---|---|
| **Live URL** | `http://10.1.75.53:3213/` |
| **Docs** | `http://10.1.75.53:3213/docs` |
| **Frontend** | `http://10.1.75.53:4213/` — [frontted-api repo](https://github.com/sunilkumar2170/frontted-api) |

CORS is enabled for the frontend origin so browser-based requests from the PondPlan UI aren't blocked.

## Testing

Validated with:
- The standard sample contour map (`contours_1m.kml`)
- Compressed KMZ archives (`.kmz`)
- Synthetic contour maps with alternative coordinate formats and elevation levels
- Multiple `land_area` boundaries of varying size, confirming catchment/coordinates/volume change correctly per boundary
- Live rainfall retrieval under real network conditions, including automatic fallback when the primary rainfall API returns `429 Too Many Requests`

## Roadmap

- [x] React + Leaflet frontend for map-based area selection and result visualization
- [x] Freehand land-boundary selection restricting analysis to a chosen parcel
- [ ] Deployment behind a load-balanced, multi-node backend (`load_balancer.py`) for stress resilience
- [ ] Persist analysis history per session

## Author

**Sunil Kumar** — B.Tech CSE, IIT Bhilai
