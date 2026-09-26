# Pond Catchment Analysis API

A robust backend API that analyzes a contour map (in **KML** or **KMZ** format), builds a terrain digital elevation model (DEM), identifies the optimal pond location/region, delineates its contributing catchment area, and estimates the expected water volume it can store — built for automated rural/village water conservation planning.

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
  "total_catchment_cells": 49,
  "catchment_polygon": [
    [81.28913619301537, 21.243782143985634],
    [81.28913619301537, 21.244022125843024],
    "... additional [longitude, latitude] boundary points ..."
  ],
  "rainfall_used_mm": 1382.66,
  "curve_number_used": 60.0,
  "runoff_depth_mm": 1198.3476056309169,
  "expected_water_volume_cubic_m": 51065.384828749055
}
```

#### Response Field Reference

| Field | Description |
|---|---|
| `pond_location` | Recommended pond coordinates (the lowest natural depression in the terrain) |
| `pond_elevation_m` | Elevation of the recommended pond site (metres) |
| `catchment_area_hectares` | Total area contributing surface runoff to the pond site |
| `total_catchment_cells` | Number of DEM grid cells included in the catchment |
| `catchment_polygon` | Boundary of the catchment area as a list of `[longitude, latitude]` points, ready for map overlay (GeoJSON-style ring) |
| `rainfall_used_mm` | Annual rainfall (mm) used in the runoff calculation, fetched live for the site's coordinates |
| `curve_number_used` | SCS Curve Number applied (reflects soil/land-use infiltration characteristics) |
| `runoff_depth_mm` | Estimated runoff depth from the SCS-CN method |
| `expected_water_volume_cubic_m` | Estimated total water volume (m³) the pond's catchment can be expected to yield annually |

### 2. Health & Status Route
- **`GET /`** — server status and available endpoints.
- **`GET /analyzeContour`** — friendly info message if the analysis endpoint is opened directly in a browser instead of called with `POST`.

---

## 🛠️ Architectural Approach & Hydrological Modeling

1. **KML / KMZ Ingestion & Parsing (`kml_parser.py`)**
   - Supports both uncompressed `.kml` and compressed `.kmz` zip archives.
   - Robust multi-attribute elevation extraction (reads elevation from `<name>`, `<ExtendedData>`, `<description>`, or 3D coordinate tuples `(lon, lat, elev)`).
   - Zero hardcoding of geographic coordinates — fully generalizes to any valid contour map.

2. **Surface Interpolation & Pseudo-DEM (`terrain_processor.py`)**
   - Flattens scattered contour polyline vertices into continuous geospatial coordinates (x, y, z).
   - Constructs a regular elevation grid (DEM) using SciPy's 2D linear barycentric interpolation (`scipy.interpolate.griddata`).

3. **Optimal Pond Site Selection (`catchment_analyzer.py`)**
   - Uses an 8-neighborhood local minimum detector to locate natural terrain depressions/sinks.
   - Selects the deepest, most viable depression as the primary pond outlet point.

4. **D8 Flow Direction & Catchment Delineation (`catchment_analyzer.py`)**
   - Computes steepest-descent flow vectors for every DEM cell using standard D8 hydrological flow modeling.
   - Performs a reverse Breadth-First Search (BFS) starting from the pond sink to trace all contributing upstream cells.

5. **Geodesic Catchment Area Estimation (`catchment_analyzer.py`)**
   - Computes cell dimensions in metres using latitude-corrected geodesic scaling (1° lat ≈ 111 km, 1° lon ≈ 111 km × cos(latitude)).
   - Calculates total contributing area in hectares (1 ha = 10,000 m²).

6. **Catchment Boundary Polygon (`catchment_analyzer.py`)**
   - Converts each contributing DEM cell into a small square polygon and merges them (via Shapely's `unary_union`) into a single catchment boundary.
   - Returns the boundary as an ordered list of `[longitude, latitude]` coordinates, directly consumable by mapping libraries (e.g. Leaflet) for visual overlay.

7. **Live Rainfall Retrieval (`rainfall_service.py`)**
   - Fetches the past year's rainfall for the recommended pond's exact coordinates from the **Open-Meteo Historical Weather API**, with automatic fallback to the **NASA POWER API** if the primary source is unavailable or rate-limited.
   - Falls back to a fixed default value only if both live sources fail, so the pipeline never breaks due to a network issue.
   - Caches results in memory per location to minimize repeated external API calls.

8. **Runoff & Water Volume Estimation (`catchment_analyzer.py`)**
   - Applies the **SCS Curve Number (CN) method**, a standard hydrological model, to estimate how much of the rainfall over the catchment becomes actual surface runoff:
     - `S = (25400 / CN) − 254` (potential maximum retention, mm)
     - `Q = (P − 0.2S)² / (P + 0.8S)` (runoff depth, mm)
   - Converts the runoff depth into a total expected water volume (m³) using the catchment area.

---

## 📁 Project Structure

```
pond-catchment-api/
├── main.py                 # FastAPI application, route handlers, and request orchestration
├── kml_parser.py            # KML & KMZ parser with robust elevation extraction
├── terrain_processor.py     # Grid interpolation & DEM construction
├── catchment_analyzer.py    # Local minima detection, D8 flow routing, BFS catchment tracing,
│                             # catchment polygon generation, and SCS-CN water volume estimation
├── rainfall_service.py      # Live rainfall retrieval (Open-Meteo + NASA POWER fallback, cached)
├── models.py                # Pydantic response models
├── requirements.txt         # Dependencies
├── contours_1m.kml          # Sample contour map for testing
└── README.md                # Documentation & report
```

---

## 🏃 Running Locally

1. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Interactive Swagger API Docs:**
   Open `http://localhost:8000/docs` in your browser.

---

## 🧪 Testing

The API was validated with:
- The standard sample contour map (`contours_1m.kml`).
- Compressed KMZ archives (`.kmz`).
- Synthetic contour maps with alternative coordinate formats and elevation levels.
- Live rainfall retrieval under real network conditions, including automatic fallback behaviour when the primary rainfall API returned `429 Too Many Requests`.

---

## 🔮 Planned / In Progress

- React + Leaflet frontend for map-based area selection and result visualization (catchment polygon and pond marker overlay).
- Deployment behind a load-balanced, multi-node backend (`load_balancer.py`) for stress resilience.

---

## 👨‍💻 Author
Sunil Kumar — B.Tech CSE, IIT Bhilai
