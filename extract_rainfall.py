import ee
from datetime import datetime, timedelta

def extract_rainfall(grid_centers, export_desc="Mumbai_RAINFALL_Export"):

    end_date = datetime.utcnow() - timedelta(days=10)  # 10 days before today
    start_date = end_date - timedelta(days=365)

    # Load ERA5-Land Daily Aggregated dataset
    dataset = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
        .select("total_precipitation_sum")  # Daily total precipitation (meters)

    # Create FeatureCollection from grid centers
    features = [
        ee.Feature(ee.Geometry.Point(lon, lat), {'Latitude': lat, 'Longitude': lon})
        for lat, lon in grid_centers.reshape(-1, 2)
    ]
    fc = ee.FeatureCollection(features)

    def extract(image):
        date = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd")
        reduced = image.multiply(1000).reduceRegions(  # Convert m ➝ mm
            collection=fc,
            reducer=ee.Reducer.mean(),
            scale=1000,
            tileScale=2
        )
        return reduced.map(lambda f: f.set({
            "Date": date,
            "Rainfall_mm": ee.Algorithms.If(f.get("mean"), f.get("mean"), -999)
        }))

    result = dataset.map(extract).flatten()

    # Export to Google Drive
    task = ee.batch.Export.table.toDrive(
        collection=result.select(["Rainfall_mm"]),
        description="Rainfall_Export",
        folder="EarthEngine",
        fileNamePrefix=export_desc,
        fileFormat="CSV"
    )
    task.start()
    print(f"Rainfall export started. Check Earth Engine Tasks tab or your Google Drive ({export_desc}.csv) once completed.")
