import os
import shutil
import tempfile
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException

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
    description="Analyzes contour maps (KML/KMZ) to determine optimal pond location and catchment area.",
    version="1.0.0"
)


@app.get("/")
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


# NEW (kept from the old local version): a friendly info message
# if someone opens /analyzeContour directly in a browser (GET request)
# instead of sending a POST with a file.
@app.get("/analyzeContour")
def analyze_contour_info():
    return {
        "message": "Pond Catchment API is running successfully",
        "method": "Use POST to upload a KML/KMZ file using field name 'contour_map'",
        "docs": "/docs"
    }


async def process_contour_file(uploaded_file: UploadFile) -> CatchmentResponse:
    suffix = os.path.splitext(uploaded_file.filename)[1] if uploaded_file.filename else ".kml"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = temp_file.name
        shutil.copyfileobj(uploaded_file.file, temp_file)

    try:
        contours = parse_contours_kml(temp_path)
        if not contours:
            raise HTTPException(status_code=400, detail="No valid contours found in the uploaded file.")

        grid_x, grid_y, grid_z = build_elevation_grid(contours)

        minima = find_local_minima(grid_z)
        if not minima:
            raise HTTPException(status_code=422, detail="No suitable pond location found in terrain.")

        best = pick_best_pond_location(grid_z, minima)
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
    file: UploadFile = File(None, description="Alternative field name for KML/KMZ file")
):
    upload = contour_map or file
    if not upload:
        raise HTTPException(
            status_code=400,
            detail="File is required under field 'contour_map' (or 'file')."
        )
    return await process_contour_file(upload)


@app.post("/findCatchment", response_model=CatchmentResponse)
async def find_catchment(
    contour_map: UploadFile = File(None, description="KML/KMZ contour map file"),
    file: UploadFile = File(None, description="Alternative field name for KML/KMZ file")
):
    upload = contour_map or file
    if not upload:
        raise HTTPException(
            status_code=400,
            detail="File is required under field 'contour_map' (or 'file')."
        )
    return await process_contour_file(upload)