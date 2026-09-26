from typing import List
from pydantic import BaseModel


class PondLocation(BaseModel):
    longitude: float
    latitude: float


class CatchmentResponse(BaseModel):
    filename: str
    pond_location: PondLocation
    pond_elevation_m: float
    catchment_area_hectares: float
    total_catchment_cells: int
    catchment_polygon: List[List[float]]

    rainfall_used_mm: float
    curve_number_used: float
    runoff_depth_mm: float
    expected_water_volume_cubic_m: float