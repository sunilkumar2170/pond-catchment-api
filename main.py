import os
import shutil
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException

from kml_parser import parse_contours_kml
from terrain_processor import build_elevation_grid
from catchment_analyzer import (
    find_local_minima,
    pick_best_pond_location,
    grid_index_to_coordinates,
    compute_flow_direction,
    trace_catchment,
    calculate_catchment_area
)
from models import CatchmentResponse, PondLocation


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
        "accepted_file_field": "contour_map",
        "docs_url": "/docs"
    }


async def process_contour_file(
    uploaded_file: UploadFile
) -> CatchmentResponse:

    suffix = (
        os.path.splitext(uploaded_file.filename)[1]
        if uploaded_file.filename
        else ".kml"
    )

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    ) as temp_file:

        temp_path = temp_file.name
        shutil.copyfileobj(uploaded_file.file, temp_file)

    try:
        contours = parse_contours_kml(temp_path)

        if not contours:
            raise HTTPException(
                status_code=400,
                detail="No valid contours found in the uploaded file."
            )

        grid_x, grid_y, grid_z = build_elevation_grid(contours)

        minima = find_local_minima(grid_z)

        if not minima:
            raise HTTPException(
                status_code=422,
                detail="No suitable pond location found in terrain."
            )

        best = pick_best_pond_location(grid_z, minima)

        lon, lat = grid_index_to_coordinates(
            grid_x,
            grid_y,
            best
        )

        flow_dir = compute_flow_direction(grid_z)

        catchment_cells = trace_catchment(
            flow_dir,
            best
        )

        area_hectares, total_cells = calculate_catchment_area(
            catchment_cells,
            grid_x,
            grid_y
        )

        return CatchmentResponse(
            filename=uploaded_file.filename or "uploaded_map.kml",

            pond_location=PondLocation(
                longitude=float(lon),
                latitude=float(lat)
            ),

            pond_elevation_m=float(
                grid_z[best[0], best[1]]
            ),

            catchment_area_hectares=float(
                area_hectares
            ),

            total_catchment_cells=int(
                total_cells
            )
        )

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@app.get("/analyzeContour")
def analyze_contour_info():
    return {
        "message": "Pond Catchment API is running successfully",
        "method": "Use POST to upload a KML/KMZ file using field name 'contour_map'",
        "docs": "/docs"
    }


@app.post(
    "/analyzeContour",
    response_model=CatchmentResponse
)
async def analyze_contour(
    contour_map: UploadFile = File(...)
):
    return await process_contour_file(contour_map)


@app.post(
    "/findCatchment",
    response_model=CatchmentResponse
)
async def find_catchment(
    contour_map: UploadFile = File(...)
):
    return await process_contour_file(contour_map)
