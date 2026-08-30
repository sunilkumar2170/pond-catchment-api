import numpy as np
from collections import deque


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


def pick_best_pond_location(grid_z, minima):
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