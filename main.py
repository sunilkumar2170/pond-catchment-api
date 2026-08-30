import shutil
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
    calculate_catchment_area
)
from models import CatchmentResponse, PondLocation

app = FastAPI()


@app.post("/analyzeContour", response_model=CatchmentResponse)
async def analyze_contour(file: UploadFile = File(...)):
    # temporarily save uploaded file so kml_parser can read it
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    contours = parse_contours_kml(temp_path)
    if not contours:
        raise HTTPException(status_code=400, detail="No valid contours found in file")

    grid_x, grid_y, grid_z = build_elevation_grid(contours)

    minima = find_local_minima(grid_z)
    if not minima:
        raise HTTPException(status_code=422, detail="No suitable pond location found")

    best = pick_best_pond_location(grid_z, minima)
    lon, lat = grid_index_to_coordinates(grid_x, grid_y, best)

    flow_dir = compute_flow_direction(grid_z)
    catchment_cells = trace_catchment(flow_dir, best)
    area_hectares, total_cells = calculate_catchment_area(catchment_cells, grid_x, grid_y)

    return CatchmentResponse(
        filename=file.filename,
        pond_location=PondLocation(longitude=float(lon), latitude=float(lat)),
        pond_elevation_m=float(grid_z[best[0], best[1]]),
        catchment_area_hectares=float(area_hectares),
        total_catchment_cells=total_cells
    )