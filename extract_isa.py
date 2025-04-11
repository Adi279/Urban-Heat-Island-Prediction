import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ee

ee.Authenticate()
ee.Initialize(project='heat-islands')
    
def extract_isa():   
    # Define region of interest (ROI) and grid
    lat_min, lon_min = 18.847, 72.744
    lat_max, lon_max = 19.797, 73.712
    lat_step = 5 / 111  # ~0.045°
    lon_step = 5 / 102  # ~0.049°

    # Generate grid (5x5 km blocks)
    lat_values = np.arange(lat_min, lat_max, lat_step)
    lon_values = np.arange(lon_min, lon_max, lon_step)

    features = []
    grid_number = 0

    for lat in lat_values:
        for lon in lon_values:
            lat1 = lat
            lat2 = lat + lat_step
            lon1 = lon
            lon2 = lon + lon_step

            box = ee.Geometry.Rectangle([lon1, lat1, lon2, lat2])
            feature = ee.Feature(box, {
                'grid_number': grid_number,
                'lat_center': lat + lat_step / 2,
                'lon_center': lon + lon_step / 2
            })
            features.append(feature)
            grid_number += 1

    # Create FeatureCollection of grid boxes
    grid_fc = ee.FeatureCollection(features)

    # Load ESA WorldCover dataset and clip it to ROI
    roi = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max + lat_step])
    dataset = ee.ImageCollection('ESA/WorldCover/v100').first().clip(roi)

    # Create a mask for the built-up area (class 50 - Built-up area)
    built_up_area = dataset.eq(50)

    # Function to calculate the percentage of built-up area in each grid
    def calculate_impervious_percentage(grid):
        grid_geometry = grid.geometry()
        built_up_in_grid = built_up_area.clip(grid_geometry)

        built_up_area_m2 = built_up_in_grid.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=grid_geometry,
            scale=10,  # Higher resolution for more accuracy
            maxPixels=1e8
        ).get('Map')  # ESA WorldCover has band name 'Map'

        grid_area_m2 = 25 * 1e6  # 25 km² = 25,000,000 m²
        impervious_percentage = ee.Number(built_up_area_m2).divide(grid_area_m2).multiply(100)
        return grid.set('impervious_percentage', impervious_percentage)

    # Apply function to each grid
    grid_with_impervious = grid_fc.map(calculate_impervious_percentage)

    # Extract the results
    grid_data = []

    for grid in grid_with_impervious.getInfo()['features']:
        grid_number = grid['properties']['grid_number']
        lat_center = grid['properties']['lat_center']
        lon_center = grid['properties']['lon_center']
        impervious_percentage = grid['properties']['impervious_percentage']

        grid_data.append({
            'grid_number': grid_number,
            'lat_center': lat_center,
            'lon_center': lon_center,
            'impervious_percentage': impervious_percentage
        })

    # Convert to DataFrame
    df = pd.DataFrame(grid_data)

    # Generate 365 dates (from 1 year ago to 10 days ago)
    end_date = datetime.today() - timedelta(days=10)
    start_date = end_date - timedelta(days=365)
    date_list = [start_date + timedelta(days=i) for i in range(365)]

    # Create the final dataset
    expanded_data = []

    for date in date_list:
        for _, row in df.iterrows():
            expanded_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'grid_number': row['grid_number'],
                'lat_center': row['lat_center'],
                'lon_center': row['lon_center'],
                'impervious_percentage': row['impervious_percentage']
            })

    final_df = pd.DataFrame(expanded_data)

    # Save to CSV
    final_df.to_csv('AREA_ISA.csv', index=False)

    # Show a preview
    print(final_df.head())
    print(f"Created ISA csv file")


