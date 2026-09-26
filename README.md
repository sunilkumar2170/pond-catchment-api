# 🌊 Pond Catchment Analysis API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)](https://numpy.org)
[![SciPy](https://img.shields.io/badge/SciPy-8CAAE6?style=for-the-badge&logo=scipy&logoColor=white)](https://scipy.org)
[![Status](https://img.shields.io/badge/Phase%202-Complete%20%26%20Verified-success?style=for-the-badge)]()

> An intelligent, automated backend API that analyzes topographical contour maps (in **KML** or **KMZ** format), reconstructs a continuous 2D Digital Elevation Model (DEM), detects natural depression sinks, and estimates contributing catchment areas using standard **D8 hydrological flow routing** for village water conservation planning.

---

## 📌 Key Highlights

- **Zero Hardcoding**: Dynamically parses bounding boxes, polyline vertices, and elevation thresholds from any input KML/KMZ file worldwide.
- **Universal File Acceptance**: Natively accepts files under the evaluator variable name **`contour_map`** (with automatic fallback to **`file`**).
- **KML & KMZ Support**: Direct XML parsing for `.kml` and in-memory zip decompression for `.kmz` files.
- **Hydrological Rigor**: Deterministic 8-direction (D8) steepest gradient flow routing coupled with reverse Breadth-First Search (BFS) basin tracing.
- **Geodesic Accuracy**: Latitude-corrected WGS84 geodesic projection converting grid cells to exact metric hectares ($1\text{ ha} = 10{,}000\text{ m}^2$).

---

## 🌐 Live Backend Endpoints

| Resource | URL | Description |
|---|---|---|
| **Primary API Route** | [`http://10.1.75.53:3213/analyzeContour`](http://10.1.75.53:3213/analyzeContour) | Main terrain & catchment analysis endpoint (`POST`) |
| **Alias Route** | [`http://10.1.75.53:3213/findCatchment`](http://10.1.75.53:3213/findCatchment) | Alternative route alias for compatibility (`POST`) |
| **Interactive Docs (Swagger)** | [`http://10.1.75.53:3213/docs`](http://10.1.75.53:3213/docs) | Interactive OpenAPI / Swagger UI testing interface |
| **Root Health Check** | [`http://10.1.75.53:3213/`](http://10.1.75.53:3213/) | Server health, status, and route discovery (`GET`) |

---

## 🏗️ System Architecture & Hydrological Pipeline

```
┌───────────────────────────┐
│   KML / KMZ Upload File   │  (multipart/form-data via contour_map)
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│     kml_parser.py         │  Extracts polylines & elevation (<name>, <ExtendedData>, (x,y,z))
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│   terrain_processor.py    │  2D Barycentric Linear Interpolation -> 100x100 Pseudo-DEM Z(x,y)
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│   catchment_analyzer.py   │  1. Local Minima Kernel Detection -> Deepest Depression Sink
│                           │  2. D8 Steepest-Gradient Flow Direction Matrix
│                           │  3. Upstream BFS Flow Tracing -> Drainage Basin Cells
│                           │  4. Geodesic Metric Area Estimation (Hectares)
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│      FastAPI Response     │  Structured JSON (Pond Coords, Elevation, Catchment Area)
└───────────────────────────┘
```

---

## 🔬 Algorithmic & Mathematical Formulation

### 1. Digital Elevation Model (DEM) Interpolation
Given scattered 3D contour vertices $\{(x_k, y_k, z_k)\}_{k=1}^M$, continuous elevation heights $Z(x, y)$ are interpolated onto a uniform regular grid:
$$Z(x, y) = \text{griddata}\left(\{(x_k, y_k)\}, \{z_k\}, (x, y), \text{method}=\text{'linear'}\right)$$

### 2. Depression Sink Identification (Local Minima)
A $3 \times 3$ kernel scans interior grid cells $(i, j)$ against its 8-neighborhood $\mathcal{N}_8$:
$$\text{IsLocalMinimum}(i, j) \iff Z_{i, j} < \min_{(di, dj) \in \mathcal{N}_8 \setminus \{(0,0)\}} Z_{i+di, j+dj}$$
The global lowest depression across all candidates is selected as the optimal pond location:
$$(i^*, j^*) = \arg\min_{(i,j) \in \text{Minima}} Z(i, j)$$

### 3. D8 Surface Runoff Flow Routing
Surface water flow vectors are routed to the neighbor offering the steepest downward drop:
$$\vec{D}(i, j) = \arg\max_{(di, dj) \in \mathcal{N}_8} \frac{Z_{i, j} - Z_{i+di, j+dj}}{\text{Distance}((i,j), (i+di, j+dj))}$$

### 4. Reverse BFS Catchment Delineation
Starting at the selected outlet sink $(i^*, j^*)$, a reverse Breadth-First Search collects all upstream cells whose drainage path reaches $(i^*, j^*)$.

### 5. Geodesic Metric Area Calculation
$$\Delta X_{\text{meters}} = \Delta \text{lon} \times 111{,}000 \times \cos(\text{Latitude}_{\text{avg}})$$
$$\Delta Y_{\text{meters}} = \Delta \text{lat} \times 111{,}000$$
$$\text{Area}_{\text{Hectares}} = \frac{N_{\text{catchment\_cells}} \times (\Delta X_{\text{meters}} \cdot \Delta Y_{\text{meters}})}{10{,}000}$$

---

## 🚀 API Specification

### `POST /analyzeContour` (or `/findCatchment`)

#### Request: `multipart/form-data`
| Form Field | Type | Required | Description |
|---|---|---|---|
| `contour_map` | File | **Yes (Primary)** | `.kml` or `.kmz` contour map file |
| `file` | File | *Fallback* | Alternative parameter name accepted for compatibility |

#### Response: `application/json` (HTTP 200)
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

## ⚡ How to Run Locally

### 1. Clone the Repository
```bash
git clone https://github.com/sunilkumar2170/pond-catchment-api.git
cd pond-catchment-api
```

### 2. Create and Activate Virtual Environment (Optional)
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Launch the Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Server will be live at `http://127.0.0.1:8000`.

---

## 🧪 Testing the API

### Option A: Via cURL (Terminal)
```bash
curl -X POST "http://127.0.0.1:8000/analyzeContour" \
  -F "contour_map=@contours_1m.kml"
```

### Option B: Via Python Script
```python
import requests

url = "http://127.0.0.1:8000/analyzeContour"
with open("contours_1m.kml", "rb") as f:
    response = requests.post(url, files={"contour_map": f})

print("Status Code:", response.status_code)
print("Response JSON:", response.json())
```

### Option C: Via Interactive Swagger UI
1. Open [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs) in your browser.
2. Expand `POST /analyzeContour` $\rightarrow$ Click **Try it out**.
3. Choose your `.kml` or `.kmz` file under `contour_map`.
4. Click **Execute** and observe the structured JSON response.

---

## 📊 Experimental Results (Sample Map: `contours_1m.kml`)

| Metric | Measured Value | Hydrological Significance |
|---|---|---|
| **Contours Loaded** | 2,710 polylines | Full vector dataset parsed successfully |
| **Optimal Pond Longitude** | `81.288978° E` | Geodesic coordinate of deepest sink |
| **Optimal Pond Latitude** | `21.244862° N` | Geodesic coordinate of deepest sink |
| **Pond Base Elevation** | `268.0 m` | Lowest natural terrain depression |
| **Contributing Catchment Cells** | `49 cells` | Active draining DEM cells |
| **Estimated Catchment Area** | **`4.261317 Hectares`** | Total contributing runoff catchment |

---

## 📁 Repository Structure

```
pond-catchment-api/
│
├── main.py                 # FastAPI application, route definitions, and multipart handling
├── kml_parser.py            # Robust parser for uncompressed KML and compressed KMZ archives
├── terrain_processor.py     # 2D Barycentric grid interpolation and slope estimation
├── catchment_analyzer.py    # Local minima detection, D8 flow routing, and BFS catchment tracing
├── models.py                # Pydantic data schemas for strict response typing
├── requirements.txt         # Project dependencies (FastAPI, NumPy, SciPy, Uvicorn, etc.)
├── contours_1m.kml          # Benchmark sample contour map
└── README.md                # Project documentation and guide
```

---

## 👨‍💻 Author

**Sunil Kumar**  
- **ID Number:** `12342170`  
- **Department:** Computer Science and Engineering  
- **Institute:** Indian Institute of Technology Bhilai (IIT Bhilai)  
- **Course:** Computer System Design — Assignment 1 (Phase 2)  
- **GitHub:** [@sunilkumar2170](https://github.com/sunilkumar2170)

