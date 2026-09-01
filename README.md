# Pond Catchment Analysis API

A robust backend API that analyzes a contour map (in **KML** or **KMZ** format), builds a terrain digital elevation model (DEM), identifies the optimal pond location/region, and estimates its contributing catchment area — built for automated rural/village water conservation planning.

---

## 🚀 API Endpoints

### 1. Primary Analysis Route
- **`POST /analyzeContour`**
- **`POST /findCatchment`** *(alias)*

#### Request Format
`multipart/form-data`

| Field | Type | Description |
|---|---|---|
| `contour_map` | File | **(Primary)** KML or KMZ contour map file |
| `file` | File | *(Alternative / Fallback)* KML or KMZ file |

#### Sample Request (cURL)
```bash
curl -X POST "http://localhost:8000/analyzeContour" \
  -F "contour_map=@contours_1m.kml"
```

#### Sample Response (`application/json`)
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

### 2. Health & Status Route
- **`GET /`**
Returns server status and available endpoints.

---

## 🛠️ Architectural Approach & Hydrological Modeling

1. **KML / KMZ Ingestion & Parsing (`kml_parser.py`)**:
   - Supports both uncompressed `.kml` and compressed `.kmz` zip archives.
   - Robust multi-attribute elevation extraction (reads elevation from `<name>`, `<ExtendedData>`, `<description>`, or 3D coordinate tuples `(lon, lat, elev)`).
   - Zero hardcoding of geographic coordinates.

2. **Surface Interpolation & Pseudo-DEM (`terrain_processor.py`)**:
   - Flattens scattered contour polyline vertices into continuous geospatial coordinates $(x, y, z)$.
   - Constructs a regular elevation grid (DEM) using SciPy's 2D linear barycentric interpolation (`scipy.interpolate.griddata`).

3. **Optimal Pond Site Selection (`catchment_analyzer.py`)**:
   - Uses an 8-neighborhood local minimum detector to locate natural terrain depressions / sinks.
   - Selects the deepest, most viable depression as the primary pond outlet point.

4. **D8 Flow Direction & Catchment Delineation (`catchment_analyzer.py`)**:
   - Computes steepest descent flow vectors for every DEM cell according to standard D8 hydrological flow modeling.
   - Performs a reverse Breadth-First Search (BFS) starting from the pond sink to trace all contributing upstream cells.

5. **Geodesic Catchment Area Estimation (`catchment_analyzer.py`)**:
   - Computes cell dimensions in meters using latitude-corrected geodesic scaling ($1^\circ \text{lat} \approx 111\,\text{km}$, $1^\circ \text{lon} \approx 111\,\text{km} \times \cos(\text{latitude})$).
   - Calculates total contributing area in hectares ($1\,\text{ha} = 10,000\,\text{m}^2$).

---

## 📁 Project Structure

```
pond-catchment-api/
├── main.py                 # FastAPI application, route handlers, and parameter mapping
├── kml_parser.py            # KML & KMZ parser with robust elevation extraction
├── terrain_processor.py     # Grid interpolation & slope computation
├── catchment_analyzer.py    # Local minima detection, D8 flow routing, and BFS catchment tracing
├── models.py                # Pydantic response models
├── requirements.txt         # Dependencies
├── contours_1m.kml          # Sample contour map for testing
└── README.md                # Documentation & report
```

---

## 🏃 Running Locally

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Interactive Swagger API Docs:**
   Open `http://localhost:8000/docs` in your browser.

---

## 🧪 Testing

The API was validated with:
- The standard sample contour map (`contours_1m.kml`).
- Compressed KMZ archives (`.kmz`).
- Synthetic contour maps with alternative coordinate formats and elevation levels.

---

## 👨‍💻 Author
Sunil Kumar — B.Tech CSE, IIT Bhilai
