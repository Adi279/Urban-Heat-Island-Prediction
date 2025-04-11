import ee

from grids import generate_grid
from extract_lst import extract_lst
from extract_ndvi import extract_ndvi
from extract_rainfall import extract_rainfall
from extract_wind import extract_wind
from extract_humidity import extract_humidity
from extract_isa import extract_isa
from clustering import clustering_kmeans


from download_datsets import download_datasets

# Initialize Google Earth Engine (GEE)
ee.Authenticate()
ee.Initialize(project='heat-islands')

# Define study area
bottom_left = (18.847, 72.744)
top_right = (19.797, 73.712)

# Generate grid centers
grid_centers = generate_grid(bottom_left, top_right)
print(f"Generated {grid_centers.shape[0] * grid_centers.shape[1]} grid centers.")

# Extract LST data and save to CSV
extract_lst(grid_centers, "Area_LST")
extract_ndvi(grid_centers, "Area_NDVI")
extract_rainfall(grid_centers, "Area_RAINFALL")
extract_wind(grid_centers, "Area_WIND")
extract_humidity(grid_centers, "Area_HUMIDITY")
extract_isa()

download_datasets()

clustering_kmeans()

import subprocess
subprocess.run(["streamlit", "run", "app1.py"])
