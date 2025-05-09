import streamlit as st
import ee
import geemap.foliumap as geemap
import pandas as pd
import numpy as np
import folium



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

# Year and date
year = 2024
start_date = f'{year}-01-01'
end_date = f'{year}-12-31'

# ------------------------- Layer Functions ----------------------------

def get_lst():
    dataset = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR') \
        .filterDate(start_date, end_date).select('temperature_2m')
    lst_celsius = dataset.mean().subtract(273.15).clip(bbox)
    vis_params = {'min': -10, 'max': 50, 'palette': ['000080', '4000ff', '00ffff', '80ff00', 'ffff00', 'ff4f00', 'ff00ff']}
    return lst_celsius, vis_params, 'LST (°C)'

def get_ndvi():
    dataset = ee.ImageCollection("MODIS/061/MOD13Q1") \
        .filterDate(start_date, end_date).select('NDVI') \
        .map(lambda img: img.divide(10000)).mean().clip(bbox)
    vis_params = {'min': 0, 'max': 1, 'palette': ['white', 'green']}
    return dataset, vis_params, 'NDVI'

def get_rainfall():
    dataset = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR') \
        .filterDate(start_date, end_date).select('total_precipitation_sum')
    rainfall_mm = dataset.sum().multiply(1000).clip(bbox)
    vis_params = {'min': 0, 'max': 2000, 'palette': ['lightblue', 'blue', 'darkblue', 'purple']}
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
    vis_params = {'min': 0, 'max': 100, 'palette': ['white', 'lightcyan', 'lightskyblue', 'deepskyblue', 'cornflowerblue',
                                                    'dodgerblue', 'blue', 'mediumblue', 'darkblue', 'indigo', 'purple',
                                                    'darkviolet', 'blueviolet']}
    return humidity, vis_params, 'Relative Humidity (%)'

def get_isa():
    isa_img = ee.ImageCollection('ESA/WorldCover/v100').first().clip(bbox)
    isa_builtup = isa_img.eq(50).selfMask()
    vis_params = {'min': 0, 'max': 1, 'palette': ['red']}
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
        return image.addBands([speed, direction]).select(["wind_speed", "wind_direction"]) \
            .copyProperties(image, ["system:time_start"])

    wind = dataset.map(add_speed_dir).select("wind_speed").mean().clip(bbox)
    vis_params = {'min': 0, 'max': 15, 'palette': ['white', 'skyblue', 'blue', 'navy']}
    return wind, vis_params, 'Wind Speed (m/s)'

# ------------------------- UHI Layer Functions ----------------------------

# ------------------------- Static UHI Code Start ------------------------------
def get_uhi():
    # Load dataset
    df = pd.read_csv("latest_data.csv")

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
    Map = geemap.Map(center=map_center, zoom=9)

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
            'width': 10
        })

    styled_fc = fc.map(uhi_style)
    Map.addLayer(styled_fc.style(**{'styleProperty': 'style'}), {}, 'UHI Labels')

    Map.to_streamlit(height=600)

# ------------------------- Static UHI Code End ------------------------------

# ----------------------- Dynamic UHI Code Start --------------------------------------------------
import streamlit as st
import pandas as pd
import folium
from folium import plugins
import numpy as np

def dynamic_uhi():
    # Step 1: Load latest_data.csv into temp dataframe
    temp = pd.read_csv("latest_data.csv")

    # Step 2: Rename columns to standardized names
    temp.rename(columns={
        'LST_Celsius': 'LST',
        'Relative_Humidity_%': 'Humidity',
        'WindSpeed': 'Wind',
        'Rainfall_mm': 'Rainfall',
        'impervious_percentage': 'ISA'
    }, inplace=True)

    # Convert ISA to fraction
    temp['ISA'] = temp['ISA'] / 100.0

    # Step 3: Let user select a grid cell
    grid_cell_index = st.sidebar.selectbox("Select Grid Cell Index", temp.index)
    selected_row = temp.loc[grid_cell_index]

    # Step 4: Let user modify parameters
    new_lst = st.sidebar.slider("Modify LST (°C)", -10.0, 50.0, float(selected_row['LST']))
    new_ndvi = st.sidebar.slider("Modify NDVI", 0.0, 1.0, float(selected_row['NDVI']))
    new_rainfall = st.sidebar.slider("Modify Rainfall (mm)", 0.0, 2000.0, float(selected_row['Rainfall']))
    new_humidity = st.sidebar.slider("Modify Humidity (%)", 0.0, 100.0, float(selected_row['Humidity']))
    new_wind = st.sidebar.slider("Modify Wind Speed (m/s)", 0.0, 15.0, float(selected_row['Wind']))
    new_isa = st.sidebar.slider("Modify ISA (fraction)", 0.0, 1.0, float(selected_row['ISA']))

    # Step 5: Update temp dataframe only for selected cell
    temp.loc[grid_cell_index, 'LST'] = new_lst
    temp.loc[grid_cell_index, 'NDVI'] = new_ndvi
    temp.loc[grid_cell_index, 'Rainfall'] = new_rainfall
    temp.loc[grid_cell_index, 'Humidity'] = new_humidity
    temp.loc[grid_cell_index, 'Wind'] = new_wind
    temp.loc[grid_cell_index, 'ISA'] = new_isa

    # Step 6: Recalculate UHI Label ONLY for the modified row
    if new_lst <= 30:
        new_label = 'Low UHI'
    elif 30 < new_lst <= 35:
        new_label = 'Low-Moderate UHI'
    elif 35 < new_lst <= 40:
        new_label = 'Moderate UHI'
    elif 40 < new_lst <= 45:
        new_label = 'Moderate-High UHI'
    elif new_lst > 45:
        new_label = 'High UHI'
    else:
        new_label = 'Unknown'

    temp.loc[grid_cell_index, 'UHI_Label'] = new_label

    # Color dictionary for UHI labels
    color_dict = {
        'Low UHI': 'blue',
        'Low-Moderate UHI': 'lightblue',
        'Moderate UHI': 'orange',
        'Moderate-High UHI': 'red',
        'High UHI': 'yellow'
    }

    # Step 7: Map visualization
    # Set up map centered on Mumbai or desired region
    mumbai_lat, mumbai_lon = 19.0760, 72.8777  # Approximate center of Mumbai
    map_obj = folium.Map(location=[mumbai_lat, mumbai_lon], zoom_start=9)

    # Add grid cells as markers on the map
    for _, row in temp.iterrows():
        # Assuming each row has 'Latitude' and 'Longitude' columns for grid cell location
        lat = row['Latitude']
        lon = row['Longitude']
        
        # Get the color based on the UHI label
        uhi_label = row['UHI_Label']
        color = color_dict.get(uhi_label, 'gray')  # Default to gray if unknown label

        # Add a marker for the grid cell
        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color=color,
            fill=True,
            fill_opacity=0.6,
            popup=f"Grid Cell {row.name}: {uhi_label}",
        ).add_to(map_obj)

    # Display the map in Streamlit
    st.write("Map showing UHI Labels for Grid Cells:")
    st.components.v1.html(map_obj._repr_html_(), height=600)

    # Optionally, display the modified dataframe in a table
    st.write("Updated DataFrame with Modified UHI Label:")
    st.dataframe(temp)

# ----------------------- Dynamic UHI Code End --------------------------------------------------

def compute_uhi(df):
    df['UHI_Label'] = np.select(
        [(df['LST'] <= 30), (df['LST'] > 30) & (df['LST'] <= 35), (df['LST'] > 35)],
        ['Low UHI', 'Moderate UHI', 'High UHI'], default='Unknown'
    )
    return df

def display_uhi(df, map_title='UHI Labels'):
    features_cluster = []
    for _, row in df.iterrows():
        point = ee.Geometry.Point([row['Longitude'], row['Latitude']])
        props = {'Cluster': int(row['Cluster']), 'UHI_Label': row['UHI_Label']}
        features_cluster.append(ee.Feature(point, props))

    fc = ee.FeatureCollection(features_cluster)
    color_dict = ee.Dictionary({
        'Low UHI': 'blue', 'Moderate UHI': 'orange', 'High UHI': 'yellow'
    })

    def uhi_style(feature):
        label = feature.get('UHI_Label')
        color = color_dict.get(label)
        return feature.set('style', {'color': color, 'fillColor': color, 'width': 10})

    styled_fc = fc.map(uhi_style)

    Map = geemap.Map(center=[19.2, 73.2], zoom=9)
    Map.addLayer(styled_fc.style(**{'styleProperty': 'style'}), {}, map_title)
    Map.addLayer(grid_fc.style(color='black', fillColor='00000000', width=1), {}, '5x5 km Grid Boxes')
    Map.to_streamlit(height=600)

# ---------------------------- Streamlit UI ----------------------------

st.set_page_config(layout="wide")
st.title("Urban Heat Island (UHI) Visualiser")

option = st.sidebar.selectbox("Choose Layer", 
    ["LST", "NDVI", "Rainfall", "Humidity", "ISA", "Wind Speed", "Static UHI", "Dynamic UHI"])

if option in ["LST", "NDVI", "Rainfall", "Humidity", "ISA", "Wind Speed"]:
    layer_functions = {
        "LST": get_lst,
        "NDVI": get_ndvi,
        "Rainfall": get_rainfall,
        "Humidity": get_humidity,
        "ISA": get_isa,
        "Wind Speed": get_wind
    }
    image, vis_params, layer_name = layer_functions[option]()
    Map = geemap.Map(center=[19.2, 73.2], zoom=9)
    Map.addLayer(image, vis_params, layer_name)
    Map.addLayer(grid_fc.style(color='black', fillColor='00000000', width=1), {}, '5x5 km Grid Boxes')
    Map.to_streamlit(height=600)

elif option == "Static UHI":
    get_uhi()

elif option == "Dynamic UHI":
    dynamic_uhi()