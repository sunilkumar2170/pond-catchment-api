# AI-based Village Pond Planning System

A backend web application that analyzes contour and elevation data (in **KML/KMZ** format) to identify optimal pond locations using local depression detection, D8 surface flow routing, and catchment area delineation.

**Course:** Computer System Design (CSD)
**Status:** Phase 2 (Backend API) ✅
**Author:** Sunil Kumar (ID: `12342170`) — IIT Bhilai

---

## 🌐 Live Working Backend Endpoints

- **Live API Endpoint:** [`http://10.1.75.53:3213/analyzeContour`](http://10.1.75.53:3213/analyzeContour)
- **Interactive Swagger Docs:** [`http://10.1.75.53:3213/docs`](http://10.1.75.53:3213/docs)
- **Status Check:** [`http://10.1.75.53:3213/`](http://10.1.75.53:3213/)

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

---

## 🧪 Test the API

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

1. **Parse KML/KMZ:** Extracts vector contour polylines along with elevation values from XML nodes or decompressed KMZ archives.
2. **Interpolate Vertices:** Builds a regular continuous elevation grid (pseudo-DEM) using 2D Barycentric linear interpolation (`scipy.interpolate.griddata`).
3. **Detect Local Minima:** Scans an 8-connected neighborhood kernel to find natural terrain depression sinks.
4. **Select Pond Site:** Identifies the deepest basin sink across the terrain.
5. **Compute D8 Flow:** Determines water runoff directions following the steepest descent elevation gradient.
6. **Delineate Catchment:** Traces all upstream contributing cells draining into the pond via reverse BFS.
7. **Calculate Area:** Converts contributing cells into geodesic metric area in hectares using latitude-corrected scaling.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend & API | Python 3, FastAPI, Uvicorn |
| Data Validation | Pydantic |
| Geospatial & Parsing | XML ElementTree, ZipFile (KMZ Support) |
| Grid Interpolation | NumPy, SciPy (griddata) |
| Hydrological Routing | Custom D8 Flow Algorithm, Reverse BFS Graph Traversal |

---

## 👨‍💻 Author

**Sunil Kumar** (ID: `12342170`)
Department of Computer Science and Engineering, IIT Bhilai
GitHub: [@sunilkumar2170](https://github.com/sunilkumar2170)
