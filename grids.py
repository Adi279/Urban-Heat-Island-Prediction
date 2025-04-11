import numpy as np

def generate_grid(bottom_left, top_right):
    """
    Generate a 2D array of grid center points for the study area.

    :param bottom_left: (lat_min, lon_min) tuple
    :param top_right: (lat_max, lon_max) tuple
    :return: NumPy 2D array of grid center points [(lat, lon), ...]
    """
    
    lat_min, lon_min = bottom_left
    lat_max, lon_max = top_right

    lat_step = 5 / 111  # 1° latitude ≈ 111 km
    lon_step = 5 / 102  # 1° longitude ≈ 102 km at ~19°N

    lat_values = np.arange(lat_min, lat_max, lat_step)
    lon_values = np.arange(lon_min, lon_max, lon_step)

    grid_centers = [
        [(lat + lat_step / 2, lon + lon_step / 2) for lon in lon_values]
        for lat in lat_values
    ]

    return np.array(grid_centers)

# For testing
if __name__ == "__main__":
    bottom_left = (18.847, 72.744)
    top_right = (19.797, 73.712)
    grid = generate_grid(bottom_left, top_right)
    print(grid.shape)  # Should print (rows, cols, 2)
