import pandas as pd
import numpy as np
from grids import generate_grid
import streamlit as st

df = pd.read_csv("Final_Merged_Dataset_with_UHI_Labels.csv")
import ee
import geemap
import numpy as np
# Initialize the Earth Engine API
ee.Initialize(project='heat-islands')
# --- Define grid parameters and fix bounding box ---
lat_min, lon_min = 18.847, 72.744
lat_step = 5 / 111
lon_step = 5 / 102
lat_values = np.arange(lat_min, 19.797, lat_step)
lon_values = np.arange(lon_min, 73.712, lon_step)
lat_max = lat_values[-1] + lat_step
lon_max = lon_values[-1] + lon_step
# Grid generation for other layers
features = []
for lat in lat_values:
    for lon in lon_values:
        box = ee.Geometry.Rectangle([lon, lat, lon + lon_step, lat + lat_step])
        feature = ee.Feature(box, {
            'lat_center': lat + lat_step / 2,
            'lon_center': lon + lon_step / 2
        })
        features.append(feature)
grid_fc = ee.FeatureCollection(features)
# Create a simple map centered on Mumbai
map_center = [18.847, 72.744]  # Bottom-left of the grid
mymap = geemap.Map(center=map_center, zoom=12)
# Add the grid points to the map
mymap.addLayer(grid_fc.style(color='black', fillColor='00000000', width=1), {}, '5x5 km Grid Boxes')
df_subset = df.tail(440)[['Latitude', 'Longitude', 'Cluster', 'UHI_Label']].copy()
# 2. Convert DataFrame to a list of ee.Features
features_cluster = []
for _, row in df_subset.iterrows():
    point = ee.Geometry.Point([row['Longitude'], row['Latitude']])
    props = {
        'Cluster': int(row['Cluster']),
        'UHI_Label': row['UHI_Label']
    }
    features_cluster.append(ee.Feature(point, props))
# 3. Create a FeatureCollection
fc = ee.FeatureCollection(features_cluster)
# 1. Create the color mapping dictionary
color_dict = ee.Dictionary({
    'Low UHI': 'blue',
    'Low-Moderate UHI': 'lightblue',
    'Moderate UHI': 'orange',
    'Moderate-High UHI': 'red',
    'High UHI': 'yellow'
})
# 2. Define the styling function
def uhi_style(feature):
    label = feature.get('UHI_Label')
    color = color_dict.get(label)
    return feature.set('style', {
        'color': color,
        'fillColor': color,
    })

# 3. Apply style function
styled_fc = fc.map(uhi_style)

    # 4. Visualize on map
mymap.addLayer(styled_fc.style(**{'styleProperty': 'style'}), {}, 'UHI Labels')
mymap.to_streamlit(height=600)

# Create a dummy image to satisfy Map.addLayer
dummy_image = ee.Image().paint(grid_fc, 0, 1)  # paint grid outlines or use actual feature if needed

# Optional: Create a label-color mapping to convert UHI_Label into numeric classes
# Or just return a simple placeholder visualization
vis_params = {
    'palette': ['blue', 'lightblue', 'orange', 'red', 'yellow'],
    'min': 0,
    'max': 4
}


# import pandas as pd
# import numpy as np
# from grids import generate_grid
# import streamlit as st
# import ee
# import geemap

# def plot_uhi():
#     df = pd.read_csv("Final_Merged_Dataset_with_UHI_Labels.csv")

#     # Initialize the Earth Engine API
#     ee.Initialize(project='heat-islands')

#     # --- Define grid parameters and fix bounding box ---
#     lat_min, lon_min = 18.847, 72.744
#     lat_step = 5 / 111
#     lon_step = 5 / 102

#     lat_values = np.arange(lat_min, 19.797, lat_step)
#     lon_values = np.arange(lon_min, 73.712, lon_step)

#     lat_max = lat_values[-1] + lat_step
#     lon_max = lon_values[-1] + lon_step

#     features = []
#     for lat in lat_values:
#         for lon in lon_values:
#             box = ee.Geometry.Rectangle([lon, lat, lon + lon_step, lat + lat_step])
#             feature = ee.Feature(box, {
#                 'lat_center': lat + lat_step / 2,
#                 'lon_center': lon + lon_step / 2
#             })
#             features.append(feature)

#     grid_fc = ee.FeatureCollection(features)

#     # Create a simple map centered on Mumbai
#     map_center = [18.847, 72.744]
#     mymap = geemap.Map(center=map_center, zoom=12)

#     # Add the grid to the map
#     mymap.addLayer(grid_fc.style(color='black', fillColor='00000000', width=1), {}, '5x5 km Grid Boxes')

#     df_subset = df.tail(440)[['Latitude', 'Longitude', 'Cluster', 'UHI_Label']].copy()

#     features_cluster = []
#     for _, row in df_subset.iterrows():
#         point = ee.Geometry.Point([row['Longitude'], row['Latitude']])
#         props = {
#             'Cluster': int(row['Cluster']),
#             'UHI_Label': row['UHI_Label']
#         }
#         features_cluster.append(ee.Feature(point, props))

#     fc = ee.FeatureCollection(features_cluster)

#     color_dict = ee.Dictionary({
#         'Low UHI': 'blue',
#         'Low-Moderate UHI': 'lightblue',
#         'Moderate UHI': 'orange',
#         'Moderate-High UHI': 'red',
#         'High UHI': 'yellow'
#     })

#     def uhi_style(feature):
#         label = feature.get('UHI_Label')
#         color = color_dict.get(label)
#         return feature.set('style', {
#             'color': color,
#             'fillColor': color,
#         })

#     styled_fc = fc.map(uhi_style)

#     mymap.addLayer(styled_fc.style(**{'styleProperty': 'style'}), {}, 'UHI Labels')

#     # Return a dummy image so Streamlit doesn't break
#     dummy_image = ee.Image().paint(grid_fc, 0, 1)
#     vis_params = {
#         'palette': ['blue', 'lightblue', 'orange', 'red', 'yellow'],
#         'min': 0,
#         'max': 4
#     }

#     return dummy_image, vis_params, 'UHI'
