import ee
from datetime import datetime, timedelta

def extract_lst(grid_centers, export_desc="Mumbai_LST_Export"):
    """
    Extracts daily LST for each grid center for one year and exports to Google Drive as CSV.

    :param grid_centers: 2D NumPy array [(lat, lon), (lat, lon), ...]
    :param export_desc: Description/filename prefix for exported CSV
    """

    # Define the date range (1 year from today)
    end_date = datetime.utcnow() - timedelta(days=10)  # 10 days before today
    start_date = end_date - timedelta(days=365)

    # Load ERA5-Land dataset
    dataset = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR') \
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
        .select('temperature_2m')

    # Convert grid centers to GEE Features
    features = [
        ee.Feature(ee.Geometry.Point(lon, lat), {'Latitude': lat, 'Longitude': lon})
        for lat, lon in grid_centers.reshape(-1, 2)
    ]
    grid_feature_collection = ee.FeatureCollection(features)

    # Function to extract daily LST values
    def extract_daily_lst(image):
        date = image.date().format('YYYY-MM-dd')
        lst_celsius = image.subtract(273.15)  # Kelvin to Celsius

        reduced = lst_celsius.reduceRegions(
            collection=grid_feature_collection,
            reducer=ee.Reducer.mean(),
            scale=5000,
            tileScale=2
        )

        return reduced.map(lambda f: f.set({
            'Date': date,
            'LST_Celsius': ee.Algorithms.If(f.get('mean'), f.get('mean'), -999)
        }))

    # Map and flatten results
    daily_lst = dataset.map(extract_daily_lst).flatten()

    # Export to Google Drive
    task = ee.batch.Export.table.toDrive(
        collection=daily_lst,
        description=export_desc,
        folder='EarthEngine',  # This will go to Google Drive > EarthEngine/
        fileNamePrefix=export_desc,
        fileFormat='CSV'
    )
    task.start()
    print(f"LST Export started. Check Earth Engine Tasks tab or your Google Drive ({export_desc}.csv) once completed.")

