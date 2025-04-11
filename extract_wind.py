import ee
from datetime import datetime, timedelta

def extract_wind(grid_centers, export_desc = "Mumbai_WIND_Export"):

    # Define the date range (1 year from today)
    end_date = datetime.utcnow() - timedelta(days=10)  # 10 days before today
    start_date = end_date - timedelta(days=365)

    # Daily aggregated ERA5 wind data
    dataset = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
        .select(["u_component_of_wind_10m", "v_component_of_wind_10m"])

    # Create FeatureCollection from grid
    features = [
        ee.Feature(ee.Geometry.Point(lon, lat), {'Latitude': lat, 'Longitude': lon})
        for lat, lon in grid_centers.reshape(-1, 2)
    ]
    fc = ee.FeatureCollection(features)

    # Compute wind speed and direction
    def add_wind_bands(image):
        u = image.select("u_component_of_wind_10m")
        v = image.select("v_component_of_wind_10m")
        speed = u.hypot(v).rename("wind_speed")
        direction = v.atan2(u).multiply(180 / 3.1415927).rename("wind_direction")  # atan2(v, u) for met convention
        return image.addBands(speed).addBands(direction) \
                    .select(["wind_speed", "wind_direction"]) \
                    .copyProperties(image, ["system:time_start"])

    wind_images = dataset.map(add_wind_bands)

    # Extract daily data for each grid point
    def extract(image):
        date = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd")
        reduced = image.reduceRegions(
            collection=fc,
            reducer=ee.Reducer.mean(),
            scale=1000,
            tileScale=2
        )
        return reduced.map(lambda f: f.set({
            "Date": date,
            "WindSpeed": ee.Algorithms.If(f.get("wind_speed"), f.get("wind_speed"), -999),
            "WindDirection": ee.Algorithms.If(f.get("wind_direction"), f.get("wind_direction"), -999)
        }))

    result = wind_images.map(extract).flatten()
    

    # Export to Google Drive
    task = ee.batch.Export.table.toDrive(
        collection=result.select(["WindSpeed", "WindDirection"]),
        description="Wind_Export",
        folder="EarthEngine",
        fileNamePrefix=export_desc,
        fileFormat="CSV"
    )
    task.start()
    print(f"Wind speed/direction Export started. Check Earth Engine Tasks tab or your Google Drive ({export_desc}.csv) once completed.")
