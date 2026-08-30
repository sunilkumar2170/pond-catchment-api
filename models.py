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