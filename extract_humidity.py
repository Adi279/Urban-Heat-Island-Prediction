import ee
from datetime import datetime, timedelta

def extract_humidity(grid_centers, export_desc="Mumbai_HUMIDITY_Export"):
    """
    Extracts air temp, dew point temp, and RH for each grid cell and exports to Google Drive.
    :param grid_centers: NumPy array of grid center coordinates [(lat, lon), ...]
    """
    # Define the date range (1 year from today)
    end_date = datetime.utcnow() - timedelta(days=10)  # 10 days before today
    start_date = end_date - timedelta(days=365)

    # Load ERA5-Land dataset with required bands
    dataset = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR') \
        .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
        .select(['temperature_2m', 'dewpoint_temperature_2m'])

    # Convert from Kelvin to Celsius
    def to_celsius(image):
        return image.subtract(273.15).set('system:time_start', image.get('system:time_start'))

    celsius_dataset = dataset.map(to_celsius)

    # Compute Relative Humidity
    def compute_rh(image):
        temp = image.select('temperature_2m')
        dew = image.select('dewpoint_temperature_2m')

        es = temp.expression('6.112 * exp((17.67 * T) / (T + 243.5))', {'T': temp})
        ed = dew.expression('6.112 * exp((17.67 * Td) / (Td + 243.5))', {'Td': dew})
        rh = ed.divide(es).multiply(100).rename('relative_humidity')

        return image.addBands(rh)

    with_rh = celsius_dataset.map(compute_rh)

    # Convert grid centers to FeatureCollection
    features = [
        ee.Feature(ee.Geometry.Point(lon, lat), {'Latitude': lat, 'Longitude': lon})
        for lat, lon in grid_centers.reshape(-1, 2)
    ]
    grid_fc = ee.FeatureCollection(features)

    # Reduce daily climate data to each grid center
    def extract_features(image):
        date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd')

        reduced = image.reduceRegions(
            collection=grid_fc,
            reducer=ee.Reducer.mean(),
            scale=1000,
            tileScale=2
        )

        return reduced.map(lambda f: f.set({
            'Date': date,
            'Air_Temperature_C': ee.Algorithms.If(f.get('temperature_2m'), f.get('temperature_2m'), -999),
            'Dew_Point_Temperature_C': ee.Algorithms.If(f.get('dewpoint_temperature_2m'), f.get('dewpoint_temperature_2m'), -999),
            'Relative_Humidity_%': ee.Algorithms.If(f.get('relative_humidity'), f.get('relative_humidity'), -999)
        }))

    daily_data = with_rh.map(extract_features).flatten()

    # Export to Google Drive
    task = ee.batch.Export.table.toDrive(
        collection=daily_data,
        description=export_desc,
        folder='EarthEngine',
        fileNamePrefix=export_desc,
        fileFormat='CSV'
    )
    task.start()
    print(f"Humidity export started. Check Earth Engine Tasks tab or Google Drive ({export_desc}.csv).")
