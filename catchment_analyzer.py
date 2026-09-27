import numpy as np
from collections import deque
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union


def find_local_minima(grid_z, margin=5):
    rows, cols = grid_z.shape
    minima = []

    for i in range(margin, rows - margin):
        for j in range(margin, cols - margin):
            center = grid_z[i, j]
            if np.isnan(center):
                continue

            neighborhood = grid_z[i-1:i+2, j-1:j+2].flatten()
            neighbors_only = np.delete(neighborhood, 4)

            if np.any(np.isnan(neighbors_only)):
                continue

            if np.all(center < neighbors_only):
                minima.append((i, j))

    return minima


def pick_best_pond_location(grid_z, minima, grid_x=None, grid_y=None, boundary_polygon=None):
    if boundary_polygon and len(boundary_polygon) >= 3 and grid_x is not None and grid_y is not None:
        from shapely.prepared import prep
        poly = Polygon(boundary_polygon)
        prep_poly = prep(poly)
        min_x, min_y, max_x, max_y = poly.bounds
        
        # 1. Check if any local minima lie inside the chosen boundary
        inside_minima = []
        for r, c in minima:
            gx, gy = grid_x[r, c], grid_y[r, c]
            if min_x <= gx <= max_x and min_y <= gy <= max_y:
                pt = Point(gx, gy)
                if prep_poly.contains(pt) or prep_poly.touches(pt):
                    inside_minima.append((r, c))

        if inside_minima:
            return min(inside_minima, key=lambda idx: grid_z[idx[0], idx[1]])

        # 2. If no strict minimum in boundary, pick lowest elevation grid cell within the boundary
        rows, cols = grid_z.shape
        candidates = []
        for r in range(rows):
            for c in range(cols):
                if not np.isnan(grid_z[r, c]):
                    gx, gy = grid_x[r, c], grid_y[r, c]
                    if min_x <= gx <= max_x and min_y <= gy <= max_y:
                        pt = Point(gx, gy)
                        if prep_poly.contains(pt) or prep_poly.touches(pt):
                            candidates.append((r, c))

        if candidates:
            return min(candidates, key=lambda idx: grid_z[idx[0], idx[1]])

    if not minima:
        return None
    return min(minima, key=lambda idx: grid_z[idx[0], idx[1]])


def grid_index_to_coordinates(grid_x, grid_y, index):
    row, col = index
    return grid_x[row, col], grid_y[row, col]


def compute_flow_direction(grid_z):
    rows, cols = grid_z.shape
    flow_dir = np.empty((rows, cols), dtype=object)

    directions = [(-1,-1),(-1,0),(-1,1),
                  (0,-1),        (0,1),
                  (1,-1), (1,0), (1,1)]

    for i in range(1, rows - 1):
        for j in range(1, cols - 1):
            center = grid_z[i, j]
            lowest_neighbor = None
            lowest_elevation = center

            for di, dj in directions:
                ni, nj = i + di, j + dj
                neighbor_elev = grid_z[ni, nj]
                if neighbor_elev < lowest_elevation:
                    lowest_elevation = neighbor_elev
                    lowest_neighbor = (di, dj)

            flow_dir[i, j] = lowest_neighbor

    return flow_dir


def trace_catchment(flow_dir, outlet):
    rows, cols = flow_dir.shape
    visited = set()
    queue = deque([outlet])
    visited.add(outlet)

    directions = [(-1,-1),(-1,0),(-1,1),
                  (0,-1),        (0,1),
                  (1,-1), (1,0), (1,1)]

    while queue:
        current = queue.popleft()
        ci, cj = current

        for di, dj in directions:
            ni, nj = ci + di, cj + dj

            if ni < 0 or ni >= rows or nj < 0 or nj >= cols:
                continue
            if (ni, nj) in visited:
                continue

            neighbor_flow = flow_dir[ni, nj]
            if neighbor_flow is not None:
                target_i = ni + neighbor_flow[0]
                target_j = nj + neighbor_flow[1]
                if (target_i, target_j) == current:
                    visited.add((ni, nj))
                    queue.append((ni, nj))

    return visited


def calculate_catchment_area(catchment_cells, grid_x, grid_y):
    cell_width_deg = abs(grid_x[1, 0] - grid_x[0, 0])
    cell_height_deg = abs(grid_y[0, 1] - grid_y[0, 0])

    avg_lat = np.mean(grid_y)
    meters_per_deg_lat = 111000
    meters_per_deg_lon = 111000 * np.cos(np.radians(avg_lat))

    cell_width_m = cell_width_deg * meters_per_deg_lon
    cell_height_m = cell_height_deg * meters_per_deg_lat

    total_cells = len(catchment_cells)
    total_area_sqm = total_cells * cell_width_m * cell_height_m
    total_area_hectares = total_area_sqm / 10000

    return total_area_hectares, total_cells


# =====================================================================
# Water volume estimation using the SCS Curve Number (CN) method.
# =====================================================================

DEFAULT_ANNUAL_RAINFALL_MM = 1100.0
DEFAULT_CURVE_NUMBER = 60.0


def estimate_water_volume(
    catchment_area_hectares,
    rainfall_mm=DEFAULT_ANNUAL_RAINFALL_MM,
    curve_number=DEFAULT_CURVE_NUMBER
):
    S = (25400.0 / curve_number) - 254.0
    initial_abstraction = 0.2 * S

    if rainfall_mm <= initial_abstraction:
        runoff_depth_mm = 0.0
    else:
        runoff_depth_mm = ((rainfall_mm - initial_abstraction) ** 2) / (rainfall_mm + 0.8 * S)

    catchment_area_sqm = catchment_area_hectares * 10000.0
    runoff_depth_m = runoff_depth_mm / 1000.0
    volume_cubic_m = runoff_depth_m * catchment_area_sqm

    return float(runoff_depth_mm), float(volume_cubic_m)


# =====================================================================
# NEW: Catchment polygon (boundary shape) generation.
# Converts the set of catchment grid cells into a single merged
# polygon boundary that can be sent to the frontend for map overlay.
# =====================================================================

def get_catchment_polygon(catchment_cells, grid_x, grid_y):
    """
    Converts catchment grid cells into a polygon boundary
    (a list of [longitude, latitude] coordinate pairs).
    """
    cell_width = abs(grid_x[1, 0] - grid_x[0, 0])
    cell_height = abs(grid_y[0, 1] - grid_y[0, 0])

    cell_polygons = []
    for row, col in catchment_cells:
        center_x = grid_x[row, col]
        center_y = grid_y[row, col]

        x1 = center_x - cell_width / 2
        x2 = center_x + cell_width / 2
        y1 = center_y - cell_height / 2
        y2 = center_y + cell_height / 2

        cell_polygon = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)])
        cell_polygons.append(cell_polygon)

    if not cell_polygons:
        return []

    catchment_shape = unary_union(cell_polygons)

    if catchment_shape.geom_type == "MultiPolygon":
        catchment_shape = max(catchment_shape.geoms, key=lambda p: p.area)

    coordinates = list(catchment_shape.exterior.coords)
    return [[float(x), float(y)] for x, y in coordinates]