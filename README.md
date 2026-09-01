<div align="center">

# 🏞️ AI-based Village Pond Planning System

**Automated pond-site selection from contour data using terrain interpolation, D8 flow routing, and catchment delineation.**



**Course:** Computer System Design (CSD) &nbsp;|&nbsp; **Author:** Sunil Kumar (`12342170`) — IIT Bhilai

**🔗 Backend URL:** [`http://10.1.75.53:3213`](http://10.1.75.53:3213/) &nbsp;|&nbsp; **📘 API Docs:** [`http://10.1.75.53:3213/docs`](http://10.1.75.53:3213/docs)

[Live API](#-live-working-backend-endpoints) · [Quick Start](#-quick-start) · [How It Works](#️-how-it-works) · [Tech Stack](#️-tech-stack)

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Live Working Backend Endpoints](#-live-working-backend-endpoints)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [Testing the API](#-testing-the-api)
- [How It Works](#️-how-it-works)
- [Tech Stack](#️-tech-stack)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)
- [Author](#-author)

---

## 🔎 Overview

Village-level pond planning has traditionally relied on manual site surveys. This project automates the process: given nothing but a **contour map exported as KML/KMZ**, the backend reconstructs a pseudo-Digital Elevation Model (DEM), finds the most promising natural depression, and computes exactly how much land area drains into it — giving planners a data-backed pond site and catchment size in seconds.

---

## 🌐 Live Working Backend Endpoints

| Endpoint | URL |
|---|---|
| **Analyze Contour** | [`http://10.1.75.53:3213/analyzeContour`](http://10.1.75.53:3213/analyzeContour) |
| **Swagger Docs** | [`http://10.1.75.53:3213/docs`](http://10.1.75.53:3213/docs) |
| **Health Check** | [`http://10.1.75.53:3213/`](http://10.1.75.53:3213/) |

> ⚠️ This is a local/lab-network IP — reachable only from within the same network as the deployment machine.

---

## 📁 Project Structure

```text
pond-catchment-api/
├── main.py                 # FastAPI service & route handlers (/analyzeContour, /findCatchment)
├── kml_parser.py            # KML & KMZ parser with multi-format elevation extraction
├── terrain_processor.py     # 2D Barycentric grid interpolation & pseudo-DEM builder
├── catchment_analyzer.py    # Local minima detection, D8 flow routing, and BFS catchment tracing
├── models.py                # Pydantic data schemas & response models
├── requirements.txt         # Project dependencies
├── contours_1m.kml          # Sample benchmark contour file for testing
└── README.md                # Project documentation
```

---

## ⚡ Quick Start

```bash
# 1. Clone repository
git clone https://github.com/sunilkumar2170/pond-catchment-api.git
cd pond-catchment-api

# 2. Setup virtual environment
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be live at `http://localhost:8000`.

---

## 📡 API Reference

| Method | Route | Description | Body |
|---|---|---|---|
| `POST` | `/analyzeContour` | Full pipeline: parses contours, builds DEM, finds pond site, computes catchment | `multipart/form-data` — field `contour_map` or `file` (KML/KMZ) |
| `POST` | `/findCatchment` | Computes catchment area for a given pond coordinate on an uploaded contour file | `multipart/form-data` + query params |
| `GET` | `/` | Health/status check | — |
| `GET` | `/docs` | Interactive Swagger UI | — |

---

## 🧪 Testing the API

### 1. Using cURL

```bash
curl -X POST "http://localhost:8000/analyzeContour" \
  -F "contour_map=@contours_1m.kml"
```

> **Note:** Both `contour_map` and `file` field names are supported.

### 2. Interactive Documentation

Open your browser at: `http://localhost:8000/docs`

### 3. Sample JSON Response

```json
{
  "filename": "contours_1m.kml",
  "pond_location": {
    "longitude": 81.28897840326482,
    "latitude": 21.24486206234389
  },
  "pond_elevation_m": 268.0,
  "catchment_area_hectares": 4.261316548620606,
  "total_catchment_cells": 49
}
```

---

## ⚙️ How It Works

```
KML/KMZ Contours
       │
       ▼
1. Parse KML/KMZ ─────────► extract polylines + elevation
       │
       ▼
2. Interpolate Vertices ──► build pseudo-DEM (SciPy griddata, barycentric)
       │
       ▼
3. Detect Local Minima ───► 8-connected neighborhood scan for sinks
       │
       ▼
4. Select Pond Site ──────► deepest basin sink on terrain
       │
       ▼
5. Compute D8 Flow ───────► steepest-descent direction per cell
       │
       ▼
6. Delineate Catchment ───► reverse BFS over upstream contributing cells
       │
       ▼
7. Calculate Area ────────► geodesic, latitude-corrected hectares
       │
       ▼
   Pond Site + Catchment Report
```

1. **Parse KML/KMZ** — Extracts vector contour polylines along with elevation values from XML nodes or decompressed KMZ archives.
2. **Interpolate Vertices** — Builds a regular continuous elevation grid (pseudo-DEM) using 2D Barycentric linear interpolation (`scipy.interpolate.griddata`).
3. **Detect Local Minima** — Scans an 8-connected neighborhood kernel to find natural terrain depression sinks.
4. **Select Pond Site** — Identifies the deepest basin sink across the terrain.
5. **Compute D8 Flow** — Determines water runoff directions following the steepest descent elevation gradient.
6. **Delineate Catchment** — Traces all upstream contributing cells draining into the pond via reverse BFS.
7. **Calculate Area** — Converts contributing cells into geodesic metric area in hectares using latitude-corrected scaling.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend & API | Python 3, FastAPI, Uvicorn |
| Data Validation | Pydantic |
| Geospatial & Parsing | XML ElementTree, ZipFile (KMZ Support) |
| Grid Interpolation | NumPy, SciPy (`griddata`) |
| Hydrological Routing | Custom D8 Flow Algorithm, Reverse BFS Graph Traversal |

---

## 🗺️ Roadmap

- [ ] Multi-pond ranking (top-N candidate sites, not just the deepest sink)
- [ ] Support for raw `.tif`/`.asc` DEM input alongside KML/KMZ
- [ ] Frontend map viewer (Leaflet/Mapbox) for visualizing pond + catchment overlays
- [ ] Rainfall-runoff volume estimation (SCS Curve Number method)
- [ ] Dockerized deployment
- [ ] Unit tests for parser, interpolation, and flow-routing modules

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m "Add: your feature"`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---


---



</div>
