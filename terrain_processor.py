import numpy as np
from scipy.interpolate import griddata


def build_elevation_grid(contours, grid_resolution=100):
    xs, ys, zs = [], [], []
    for contour in contours:
        elevation = contour['elevation']
        for lon, lat in contour['coordinates']:
            xs.append(lon)
            ys.append(lat)
            zs.append(elevation)

    xs, ys, zs = np.array(xs), np.array(ys), np.array(zs)

    min_x, max_x = xs.min(), xs.max()
    min_y, max_y = ys.min(), ys.max()

    grid_x, grid_y = np.mgrid[
        min_x:max_x:complex(grid_resolution),
        min_y:max_y:complex(grid_resolution)
    ]

    grid_z = griddata((xs, ys), zs, (grid_x, grid_y), method='linear')

    return grid_x, grid_y, grid_z


def compute_slope(grid_z, cell_size=1.0):
    dz_dy, dz_dx = np.gradient(grid_z, cell_size)
    slope = np.sqrt(dz_dx ** 2 + dz_dy ** 2)
    return slope