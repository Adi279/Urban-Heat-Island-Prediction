import pandas as pd
from datetime import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

def merge_lst_ndvi():
    # --- Authenticate Google Drive ---
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)

    # --- Download files by filename ---
    def download_file(file_name, local_path):
        file_list = drive.ListFile({'q': f"title='{file_name}' and trashed=false"}).GetList()
        if not file_list:
            raise FileNotFoundError(f"{file_name} not found on Google Drive")
        file = file_list[0]
        file.GetContentFile(local_path)
        print(f"Downloaded: {file_name}")

    download_file("AREA_LST.csv", "AREA_LST.csv")
    download_file("AREA_NDVI.csv", "AREA_NDVI.csv")

    # --- Load and process the files ---
    lst_df = pd.read_csv("AREA_LST.csv")
    ndvi_df = pd.read_csv("AREA_NDVI.csv")

    # --- Preprocess NDVI ---
    # Extract date and grid number from system:index
    ndvi_df['Date'] = ndvi_df['system:index'].apply(lambda x: "_".join(x.split("_")[:3]))
    ndvi_df['grid_number'] = ndvi_df['system:index'].apply(lambda x: int(x.split("_")[-1]))
    ndvi_df['Date'] = pd.to_datetime(ndvi_df['Date'], format='%Y_%m_%d')

    # Convert AREA_LST date to datetime
    lst_df['Date'] = pd.to_datetime(lst_df['Date'])

    # Add grid_number to lst_df (assuming system:index column exists)
    lst_df['grid_number'] = lst_df['system:index'].apply(lambda x: int(x.split("_")[-1]))

    # Create a lookup dictionary for each grid: {grid_number: dataframe}
    ndvi_lookup = {
        grid: df.sort_values("Date") for grid, df in ndvi_df.groupby("grid_number")
    }

    def find_ndvi_value(row):
        date = row['Date']
        grid = row['grid_number']
        if grid not in ndvi_lookup:
            return None
        df = ndvi_lookup[grid]
        match = df[df['Date'] == date]
        if not match.empty:
            return match['NDVI'].values[0]
        prev = df[df['Date'] < date]
        if not prev.empty:
            return prev.iloc[-1]['NDVI']
        return df.iloc[0]['NDVI']

    lst_df['NDVI'] = lst_df.apply(find_ndvi_value, axis=1)
    output_file = "AREA_LST_with_NDVI.csv"
    lst_df.to_csv(output_file, index=False)
    print(f"Merged CSV saved as {output_file}")

    # --- Find the EarthEngine folder ID ---
    folder_list = drive.ListFile({'q': "mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    earthengine_folder = next((f for f in folder_list if f['title'] == 'EarthEngine'), None)

    if not earthengine_folder:
        raise Exception(" 'EarthEngine' folder not found in your Drive!")

    # --- Upload the CSV into 'EarthEngine' folder ---
    uploaded_file = drive.CreateFile({
        'title': output_file,
        'parents': [{'id': earthengine_folder['id']}]
    })
    uploaded_file.SetContentFile(output_file)
    uploaded_file.Upload()
    print(f"Uploaded to Google Drive > EarthEngine > {output_file}")