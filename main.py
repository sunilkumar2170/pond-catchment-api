import os
import shutil
import tempfile
import json
from typing import Optional
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from kml_parser import parse_contours_kml
from terrain_processor import build_elevation_grid
from catchment_analyzer import (
    find_local_minima,
    pick_best_pond_location,
    grid_index_to_coordinates,
    compute_flow_direction,
    trace_catchment,
    calculate_catchment_area,
    estimate_water_volume,
    get_catchment_polygon,
    DEFAULT_ANNUAL_RAINFALL_MM,
    DEFAULT_CURVE_NUMBER
)
from models import CatchmentResponse, PondLocation
from rainfall_service import fetch_annual_rainfall

app = FastAPI(
    title="Pond Catchment Analysis API",
    description="Analyzes contour maps (KML/KMZ) to determine optimal pond location and catchment area, with optional land boundary constraint.",
    version="1.0.0"
)

# Enable CORS for frontend (React, Vite, Postman, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "online"}


@app.get("/api-status")
def read_root():
    return {
        "status": "online",
        "message": "Pond Catchment Analysis API is running.",
        "endpoints": [
            "POST /analyzeContour",
            "POST /findCatchment"
        ],
        "accepted_file_field": "contour_map (or file)",
        "docs_url": "/docs"
    }


# Friendly info message if someone opens /analyzeContour directly in a browser (GET request)
@app.get("/analyzeContour")
def analyze_contour_info():
    return {
        "message": "Pond Catchment API is running successfully",
        "method": "Use POST to upload a KML/KMZ file using field name 'contour_map', with optional 'land_boundary' JSON",
        "docs": "/docs"
    }


async def process_contour_file(uploaded_file: UploadFile, land_boundary: Optional[str] = None) -> CatchmentResponse:
    boundary_coords = None
    if land_boundary:
        try:
            parsed = json.loads(land_boundary)
            if isinstance(parsed, list) and len(parsed) >= 3:
                boundary_coords = parsed
        except Exception:
            boundary_coords = None

    suffix = os.path.splitext(uploaded_file.filename)[1] if uploaded_file.filename else ".kml"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = temp_file.name
        shutil.copyfileobj(uploaded_file.file, temp_file)

    try:
        contours = parse_contours_kml(temp_path)
        if not contours:
            raise HTTPException(status_code=400, detail="No valid contours found in the uploaded file.")

        # ── KEY FIX: Filter contour points to those INSIDE the drawn boundary ──
        # This ensures the ENTIRE pipeline (grid building, catchment tracing,
        # runoff calculation) operates only on terrain within the selected parcel.
        used_boundary_filter = False
        if boundary_coords and len(boundary_coords) >= 3:
            from shapely.geometry import Point as SPoint, Polygon as SPolygon
            from shapely.prepared import prep
            from shapely.validation import make_valid
            try:
                boundary_poly = make_valid(SPolygon(boundary_coords))
            except Exception:
                boundary_poly = SPolygon(boundary_coords)

            prep_poly = prep(boundary_poly)
            min_lon, min_lat, max_lon, max_lat = boundary_poly.bounds

            filtered_contours = []
            for contour in contours:
                filtered_pts = []
                for lon, lat in contour['coordinates']:
                    if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                        pt = SPoint(lon, lat)
                        if prep_poly.contains(pt) or prep_poly.touches(pt):
                            filtered_pts.append((lon, lat))
                if filtered_pts:
                    filtered_contours.append({
                        'elevation': contour['elevation'],
                        'coordinates': filtered_pts
                    })

            # Need at least 2 elevation levels to build a meaningful DEM
            if len(filtered_contours) >= 2:
                contours = filtered_contours
                used_boundary_filter = True
            # else: fall back to full map; boundary still used for pond-siting below

        grid_x, grid_y, grid_z = build_elevation_grid(contours)

        minima = find_local_minima(grid_z)

        # When contours were already filtered, the entire grid IS the boundary area,
        # so pass boundary_coords only when we did NOT filter (for pond-siting fallback)
        best = pick_best_pond_location(
            grid_z, minima, grid_x, grid_y,
            None if used_boundary_filter else boundary_coords
        )
        if best is None:
            if minima:
                best = min(minima, key=lambda idx: grid_z[idx[0], idx[1]])
            else:
                raise HTTPException(status_code=422, detail="No suitable pond location found in selected land boundary.")

        lon, lat = grid_index_to_coordinates(grid_x, grid_y, best)

        flow_dir = compute_flow_direction(grid_z)
        catchment_cells = trace_catchment(flow_dir, best)
        area_hectares, total_cells = calculate_catchment_area(catchment_cells, grid_x, grid_y)

        catchment_polygon = get_catchment_polygon(catchment_cells, grid_x, grid_y)

        rainfall_mm = await fetch_annual_rainfall(latitude=float(lat), longitude=float(lon))

        runoff_depth_mm, water_volume_cubic_m = estimate_water_volume(
            catchment_area_hectares=area_hectares,
            rainfall_mm=rainfall_mm,
            curve_number=DEFAULT_CURVE_NUMBER
        )

        return CatchmentResponse(
            filename=uploaded_file.filename or "uploaded_map.kml",
            pond_location=PondLocation(longitude=float(lon), latitude=float(lat)),
            pond_elevation_m=float(grid_z[best[0], best[1]]),
            catchment_area_hectares=float(area_hectares),
            total_catchment_cells=int(total_cells),
            catchment_polygon=catchment_polygon,

            rainfall_used_mm=rainfall_mm,
            curve_number_used=DEFAULT_CURVE_NUMBER,
            runoff_depth_mm=runoff_depth_mm,
            expected_water_volume_cubic_m=water_volume_cubic_m
        )
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass



@app.post("/analyzeContour", response_model=CatchmentResponse)
async def analyze_contour(
    contour_map: UploadFile = File(None, description="KML/KMZ contour map file"),
    file: UploadFile = File(None, description="Alternative field name for KML/KMZ file"),
    land_boundary: Optional[str] = Form(None, description="Optional JSON array of [lon, lat] coordinates")
):
    upload = contour_map or file
    if not upload:
        raise HTTPException(
            status_code=400,
            detail="File is required under field 'contour_map' (or 'file')."
        )
    return await process_contour_file(upload, land_boundary)


@app.post("/findCatchment", response_model=CatchmentResponse)
async def find_catchment(
    contour_map: UploadFile = File(None, description="KML/KMZ contour map file"),
    file: UploadFile = File(None, description="Alternative field name for KML/KMZ file"),
    land_boundary: Optional[str] = Form(None, description="Optional JSON array of [lon, lat] coordinates")
):
    upload = contour_map or file
    if not upload:
        raise HTTPException(
            status_code=400,
            detail="File is required under field 'contour_map' (or 'file')."
        )
    return await process_contour_file(upload, land_boundary)


@app.get("/")
def api_root():
    return {
        "status": "online",
        "service": "Pond Catchment Analysis API",
        "endpoints": [
            "POST /analyzeContour",
            "POST /findCatchment"
        ],
        "accepted_file_field": "contour_map (or file)",
        "docs_url": "/docs"
    }