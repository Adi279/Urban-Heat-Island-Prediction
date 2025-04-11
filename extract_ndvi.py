import ee
from datetime import datetime, timedelta
from  merge_ndvi import merge_lst_ndvi

def extract_ndvi(grid_centers, export_desc="Mumbai_NDVI_Export"):
    """
    Extracts daily NDVI for each grid center for one year and exports to Google Drive as CSV.

    :param grid_centers: 2D NumPy array [(lat, lon), (lat, lon), ...]
    :param export_desc: Description/filename prefix for exported CSV
    """

    # Define the date range (1 year from today)
    end_date = datetime.utcnow() - timedelta(days=10)  # 10 days before today
    start_date = end_date - timedelta(days=365)

    # Load MODIS NDVI dataset
    dataset = ee.ImageCollection("MODIS/061/MOD13Q1") \
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
        .select("NDVI") \
        .map(lambda image: image.divide(10000).copyProperties(image, ["system:time_start"]))

    # Convert grid centers to GEE Features
    features = [
        ee.Feature(ee.Geometry.Point(lon, lat), {'Latitude': lat, 'Longitude': lon})
        for lat, lon in grid_centers.reshape(-1, 2)
    ]
    grid_feature_collection = ee.FeatureCollection(features)

   # Function to extract daily NDVI values
    def extract_daily_ndvi(image):
        date = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd")
        reduced = image.reduceRegions(
            collection=grid_feature_collection,
            reducer=ee.Reducer.mean(),
            scale=500,
            tileScale=2
        )
        return reduced.map(lambda f: f.set({
            "Date": date,
            "NDVI": ee.Algorithms.If(f.get("mean"), f.get("mean"), -999)
        }))


    # Map and flatten results
    daily_ndvi = dataset.map(extract_daily_ndvi).flatten()

    # Export to Google Drive
    task = ee.batch.Export.table.toDrive(
        collection=daily_ndvi,
        description=export_desc,
        folder='EarthEngine',  # This will go to Google Drive > EarthEngine/
        fileNamePrefix=export_desc,
        fileFormat='CSV'
    )
    task.start()
    print(f"NDVI Export started. Check Earth Engine Tasks tab or your Google Drive ({export_desc}.csv) once completed.")
    merge_lst_ndvi()
