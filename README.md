# Pond Catchment Analysis API

A backend API that analyzes a contour map (KML format) to identify a suitable pond location and estimate its catchment area — built for automated village pond planning.

## Overview

Given a KML contour map, this API:
1. Parses contour lines and their elevation values
2. Builds an interpolated elevation surface (pseudo-DEM) from the scattered contour points
3. Identifies natural depressions (local minima) as candidate pond locations
4. Computes flow direction for every grid cell (D8 method)
5. Traces which cells drain into the selected pond location (catchment delineation via BFS)
6. Returns the pond location and total catchment area

No coordinates, locations, or results are hardcoded — everything is derived from the uploaded contour map, so the same pipeline works on any valid KML contour file.

## API Endpoint

**POST** `/analyzeContour`

**Request:** `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `file` | File | KML contour map to analyze |

**Response:** `application/json`

```json
{
  "filename": "contours_1m.kml",
  "pond_location": {
    "longitude": 81.28897840326485,
    "latitude": 21.244862062343888
  },
  "pond_elevation_m": 268.0,
  "catchment_area_hectares": 4.261316548620606,
  "total_catchment_cells": 49
}
```

**Error responses:**
- `400` — uploaded file has no valid/parseable contours
- `422` — no suitable pond location (local minimum) could be identified from the data

## Project Structure

```
pond-catchment-api/
│
├── main.py                 # FastAPI app and the /analyzeContour route
├── kml_parser.py            # Parses KML files into (elevation, coordinates) contours
├── terrain_processor.py     # Builds interpolated elevation grid + slope
├── catchment_analyzer.py    # Pond location detection, flow direction, catchment trace, area calculation
├── models.py                 # Pydantic response models
├── requirements.txt
└── contours_1m.kml           # Sample contour map used for development/testing
```

Each file has a single responsibility, so the pipeline can be extended (e.g. swapping the interpolation method, adding rainfall/runoff estimation in a later phase) without touching unrelated modules.

## Approach

1. **Parsing** — Each `<Placemark>` in the KML represents one contour line; its elevation is read from the `<name>` tag and its shape from `<coordinates>`.
2. **Interpolation** — All contour points are flattened into scattered `(x, y, z)` points and interpolated onto a regular grid using `scipy.interpolate.griddata`, producing a continuous elevation surface.
3. **Pond location** — Every interior grid cell is checked against its 8 neighbors; a cell lower than all of them is a local minimum. The deepest local minimum is chosen as the pond location.
4. **Flow direction (D8)** — For each cell, the algorithm finds which of its 8 neighbors has the lowest elevation — that's the direction water would flow.
5. **Catchment delineation** — Starting from the pond location, a breadth-first search walks backward through the flow-direction grid to collect every cell whose water eventually reaches that point.
6. **Area estimation** — The number of contributing cells is converted from grid units (degrees) to real-world area (hectares) using standard degree-to-meter conversion at the site's latitude.

## Running Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

API will be available at `http://127.0.0.1:8000/analyzeContour`.

## Testing

Tested with the provided sample map (`contours_1m.kml`) as well as an independently generated synthetic contour map with different terrain, confirming the pipeline generalizes to contour maps beyond the provided sample.

## Tech Stack

- **FastAPI** — API framework
- **NumPy / SciPy** — grid interpolation, slope, and numerical computation
- **Pydantic** — response validation and schema

## Author

Sunil Kumar — B.Tech CSE, IIT Bhilai
