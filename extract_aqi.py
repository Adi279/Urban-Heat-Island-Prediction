import pandas as pd
import requests
from datetime import timedelta
import os
from datetime import datetime, timedelta

def extract_aqi(grid_centers, filename):
    # Define the date range (1 year from today)
    end_date = datetime.utcnow() - timedelta(days=10)  # 10 days before today
    start_date = end_date - timedelta(days=365)

    API_KEY = "key" 
    API_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

    def get_aqi(lat, lon):
        params = {"lat": lat, "lon": lon, "appid": API_KEY}
        try:
            response = requests.get(API_URL, params=params)
            if response.status_code == 200:
                data = response.json()["list"][0]["components"]
                return {
                    "PM2.5": data.get("pm2_5"),
                    "PM10": data.get("pm10"),
                    "CO": data.get("co"),
                    "NOx": data.get("no2")
                }
        except Exception:
            pass
        return {"PM2.5": None, "PM10": None, "CO": None, "NOx": None}

    # Step 1: Fetch static AQI for each grid center
    static_data = []
    for i in range(grid_centers.shape[0]):  # Loop over rows (22)
        for j in range(grid_centers.shape[1]):  # Loop over columns (20)
            lat, lon = grid_centers[i, j]  # Unpack each (lat, lon) pair
            print(f"Fetching AQI for grid ({i},{j}) at ({lat:.4f}, {lon:.4f})...")
            aqi = get_aqi(lat, lon)
            static_data.append({
                "grid_number": f"{i}_{j}",
                "Latitude": lat,
                "Longitude": lon,
                "PM2.5": aqi["PM2.5"],
                "PM10": aqi["PM10"],
                "CO": aqi["CO"],
                "NOx": aqi["NOx"]
            })

    df_static = pd.DataFrame(static_data)

    # Step 2: Expand static values across daily timestamps
    date_list = [start_date + timedelta(days=i) for i in range((end_date - start_date).days)]
    expanded_data = []

    for date in date_list:
        for row in df_static.itertuples(index=False):
            expanded_data.append({
                "Date": date.strftime("%Y-%m-%d"),
                "Latitude": row.Latitude,
                "Longitude": row.Longitude,
                "PM2.5": row.PM25,
                "PM10": row.PM10,
                "CO": row.CO,
                "NOx": row.NOx
            })

    df_final = pd.DataFrame(expanded_data)

    # Step 3: Export to extract_datasets folder
    os.makedirs("extract_datasets", exist_ok=True)
    export_path = os.path.join("extract_datasets", filename)
    df_final.to_csv(export_path, index=False)


    print(f" AQI dataset saved to Google Drive > extract_datasets > {filename}")


