import streamlit as st
import ee
import geemap.foliumap as geemap
import folium
import numpy as np
import requests
import pandas as pd

# Initialize Earth Engine
ee.Initialize(project='heat-islands')

# --- Define grid parameters and fix bounding box ---
lat_min, lon_min = 18.847, 72.744
lat_step = 5 / 111
lon_step = 5 / 102

lat_values = np.arange(lat_min, 19.797, lat_step)
lon_values = np.arange(lon_min, 73.712, lon_step)

lat_max = lat_values[-1] + lat_step
lon_max = lon_values[-1] + lon_step

bbox = ee.Geometry.BBox(lon_min, lat_min, lon_max, lat_max)
roi = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])

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

# Year and date
year = 2024
start_date = f'{year}-01-01'
end_date = f'{year}-12-31'

# ------------------------- Layer Functions ----------------------------

def get_lst():
    dataset = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR') \
        .filterDate(start_date, end_date).select('temperature_2m')
    lst_celsius = dataset.mean().subtract(273.15).clip(bbox)
    vis_params = {
        'min': -10,
        'max': 50,
        'palette': ['000080', '0000d9', '4000ff', '8000ff', '0080ff', '00ffff',
                    '00ff80', '80ff00', 'daff00', 'ffff00', 'fff500', 'ffda00',
                    'ffb000', 'ffa400', 'ff4f00', 'ff2500', 'ff0a00', 'ff00ff']
    }
    return lst_celsius, vis_params, 'LST (°C)'

def get_ndvi():
    dataset = ee.ImageCollection("MODIS/061/MOD13Q1") \
        .filterDate(start_date, end_date).select('NDVI') \
        .map(lambda img: img.divide(10000)).mean().clip(bbox)
    vis_params = {
        'min': 0,
        'max': 1,
        'palette': ['white', 'green']
    }
    return dataset, vis_params, 'NDVI'

def get_rainfall():
    dataset = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR') \
        .filterDate(start_date, end_date).select('total_precipitation_sum')
    rainfall_mm = dataset.sum().multiply(1000).clip(bbox)
    vis_params = {
        'min': 0,
        'max': 2000,
        'palette': ['lightblue', 'blue', 'darkblue', 'purple']
    }
    return rainfall_mm, vis_params, 'Rainfall (mm)'

def get_humidity():
    dataset = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR') \
        .filterDate(start_date, end_date) \
        .select(['temperature_2m', 'dewpoint_temperature_2m'])

    def compute_rh(image):
        temp = image.select('temperature_2m').subtract(273.15)
        dew = image.select('dewpoint_temperature_2m').subtract(273.15)
        es = temp.expression('6.112 * exp((17.67 * T) / (T + 243.5))', {'T': temp})
        ed = dew.expression('6.112 * exp((17.67 * Td) / (Td + 243.5))', {'Td': dew})
        rh = ed.divide(es).multiply(100).rename('relative_humidity')
        return rh.set('system:time_start', image.get('system:time_start'))

    humidity = dataset.map(compute_rh).mean().clip(bbox)
    vis_params = {
        'min': 0,
        'max': 100,
        'pallette':[
            'white',         # Very Low
            'lightcyan',
            'lightskyblue',
            'deepskyblue',
            'cornflowerblue',
            'dodgerblue',
            'blue',
            'mediumblue',
            'darkblue',
            'indigo',
            'purple',        # Very High
            'darkviolet',
            'blueviolet'
        ]

    }
    return humidity, vis_params, 'Relative Humidity (%)'

def get_isa():
    isa_img = ee.ImageCollection('ESA/WorldCover/v100').first().clip(bbox)
    isa_builtup = isa_img.eq(50).selfMask()
    vis_params = {
        'min': 0,
        'max': 1,
        'palette': ['red']
    }
    return isa_builtup, vis_params, 'ISA (Built-up Area)'

def get_wind():
    dataset = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
        .filterDate(start_date, end_date) \
        .select(["u_component_of_wind_10m", "v_component_of_wind_10m"])

    def add_speed_dir(image):
        u = image.select("u_component_of_wind_10m")
        v = image.select("v_component_of_wind_10m")
        speed = u.hypot(v).rename("wind_speed")
        direction = v.atan2(u).multiply(180 / 3.1415927).rename("wind_direction")
        return image.addBands([speed, direction]) \
                    .select(["wind_speed", "wind_direction"]) \
                    .copyProperties(image, ["system:time_start"])

    wind = dataset.map(add_speed_dir).select("wind_speed").mean().clip(bbox)
    vis_params = {
        'min': 0,
        'max': 15,
        'palette': ['white', 'skyblue', 'blue', 'navy']
    }
    return wind, vis_params, 'Wind Speed (m/s)'

# ------------------------- UHI Layer ----------------------------

def get_uhi():
    # Initialize Earth Engine
    try:
        ee.Initialize(project='heat-islands')
    except Exception as e:
        ee.Authenticate()
        ee.Initialize(project='heat-islands')

    # Load dataset
    df = pd.read_csv("Final_Merged_Dataset_with_UHI_Labels.csv")

    # Define grid parameters and bounding box
    lat_min, lon_min = 18.847, 72.744
    lat_step = 5 / 111
    lon_step = 5 / 102

    lat_values = np.arange(lat_min, 19.797, lat_step)
    lon_values = np.arange(lon_min, 73.712, lon_step)

    # Grid generation
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

    # Create map
    map_center=[19.2, 73.2]
    Map = geemap.Map(center=map_center, zoom=10)

    # Add grid to map
    Map.addLayer(grid_fc.style(color='black', fillColor='00000000', width=1), {}, '5x5 km Grid Boxes')

    # Prepare UHI features
    df_subset = df.tail(440)[['Latitude', 'Longitude', 'Cluster', 'UHI_Label']].copy()
    features_cluster = []
    for _, row in df_subset.iterrows():
        point = ee.Geometry.Point([row['Longitude'], row['Latitude']])
        props = {
            'Cluster': int(row['Cluster']),
            'UHI_Label': row['UHI_Label']
        }
        features_cluster.append(ee.Feature(point, props))

    fc = ee.FeatureCollection(features_cluster)

    # Define UHI color mapping
    color_dict = ee.Dictionary({
        'Low UHI': 'blue',
        'Low-Moderate UHI': 'lightblue',
        'Moderate UHI': 'orange',
        'Moderate-High UHI': 'red',
        'High UHI': 'yellow'
    })

    def uhi_style(feature):
        label = feature.get('UHI_Label')
        color = color_dict.get(label)
        return feature.set('style', {
            'color': color,
            'fillColor': color,
            'width': 5
        })

    styled_fc = fc.map(uhi_style)
    Map.addLayer(styled_fc.style(**{'styleProperty': 'style'}), {}, 'UHI Labels')

    Map.to_streamlit(height=600)


# ---------------------------- UI ----------------------------

st.set_page_config(layout="wide")
st.title("Urban Heat Island (UHI) Visualiser")

layer_option = st.sidebar.selectbox(
    "Choose a layer to visualize",
    (
        "Final UHI",
        "NDVI (Vegetation Index)",
        "Rainfall (Precipitation)",
        "Impervious Surface Area (ISA)",
        "Wind Speed",
        "Relative Humidity",
        "Land Surface Temperature (LST)",
    )
)

Map = geemap.Map(center=[19.2, 73.2], zoom=9)


if layer_option == "Final UHI":
    get_uhi()
elif layer_option == "Impervious Surface Area (ISA)":
    image, vis_params, label = get_isa()
    Map.addLayer(image, vis_params, label)
    Map.addLayer(grid_fc.style(color='black', fillColor='00000000', width=1), {}, '5x5 km Grid Boxes')
    Map.to_streamlit(height=600)
elif layer_option == "NDVI (Vegetation Index)":
    image, vis_params, label = get_ndvi()
    Map.addLayer(image, vis_params, label)
    Map.addLayer(grid_fc.style(color='black', fillColor='00000000', width=1), {}, '5x5 km Grid Boxes')
    Map.to_streamlit(height=600)
elif layer_option == "Rainfall (Precipitation)":
    image, vis_params, label = get_rainfall()
    Map.addLayer(image, vis_params, label)
    Map.addLayer(grid_fc.style(color='black', fillColor='00000000', width=1), {}, '5x5 km Grid Boxes')
    Map.to_streamlit(height=600)
elif layer_option == "Wind Speed":
    image, vis_params, label = get_wind()
    Map.addLayer(image, vis_params, label)
    Map.addLayer(grid_fc.style(color='black', fillColor='00000000', width=1), {}, '5x5 km Grid Boxes')
    Map.to_streamlit(height=600)
elif layer_option == "Relative Humidity":
    image, vis_params, label = get_humidity()
    Map.addLayer(image, vis_params, label)
    Map.addLayer(grid_fc.style(color='black', fillColor='00000000', width=1), {}, '5x5 km Grid Boxes')
    Map.to_streamlit(height=600)
elif layer_option == "Land Surface Temperature (LST)":
    image, vis_params, label = get_lst()
    Map.addLayer(image, vis_params, label)
    Map.addLayer(grid_fc.style(color='black', fillColor='00000000', width=1), {}, '5x5 km Grid Boxes')
    Map.to_streamlit(height=600)
    

# Always show grid overlay


Map.addLayerControl()

