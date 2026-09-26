import numpy as np
from scipy.interpolate import griddata


def build_elevation_grid(contours, grid_resolution=70):
    xs, ys, zs = [], [], []
    for contour in contours:
        elevation = contour['elevation']
        for lon, lat in contour['coordinates']:
            xs.append(lon)
            ys.append(lat)
            zs.append(elevation)

    # NEW: use float32 instead of default float64 — halves memory usage
    # for every array below, with negligible precision loss for this use case
    xs = np.array(xs, dtype=np.float32)
    ys = np.array(ys, dtype=np.float32)
    zs = np.array(zs, dtype=np.float32)

    min_x, max_x = xs.min(), xs.max()
    min_y, max_y = ys.min(), ys.max()

    grid_x, grid_y = np.mgrid[
        min_x:max_x:complex(grid_resolution),
        min_y:max_y:complex(grid_resolution)
    ]

    # NEW: cast grid coordinates to float32 as well
    grid_x = grid_x.astype(np.float32)
    grid_y = grid_y.astype(np.float32)

    grid_z = griddata((xs, ys), zs, (grid_x, grid_y), method='linear')

    # NEW: griddata internally returns float64 regardless of input dtype,
    # so cast the result back down to float32 to keep the final grid small
    grid_z = grid_z.astype(np.float32)

    return grid_x, grid_y, grid_z


def compute_slope(grid_z, cell_size=1.0):
    dz_dy, dz_dx = np.gradient(grid_z, cell_size)
    slope = np.sqrt(dz_dx ** 2 + dz_dy ** 2)
    return slope.astype(np.float32)