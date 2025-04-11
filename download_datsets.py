import pandas as pd
from datetime import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

def download_datasets():
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

    download_file("AREA_HUMIDITY.csv", "AREA_HUMIDITY.csv")
    download_file("AREA_WIND.csv", "AREA_WIND.csv")
    download_file("AREA_RAINFALL.csv", "AREA_RAINFALL.csv")

    lst_ndvi_df = pd.read_csv("AREA_LST_with_NDVI.csv")
    humidity_df = pd.read_csv("AREA_HUMIDITY.csv")
    wind_df = pd.read_csv("AREA_WIND.csv")
    rainfall_df = pd.read_csv("AREA_RAINFALL.csv")
    isa_df = pd.read_csv("AREA_ISA.csv")

    lst_ndvi_df = lst_ndvi_df[['system:index','Date','Latitude','Longitude','LST_Celsius','NDVI']]
    humidity_df = humidity_df[['system:index','Air_Temperature_C','Dew_Point_Temperature_C','Relative_Humidity_%']]
    wind_df = wind_df[['system:index','WindDirection','WindSpeed']]
    rainfall_df = rainfall_df[['system:index','Rainfall_mm']]
    isa_df = isa_df[['impervious_percentage']]

    final_df = lst_ndvi_df.merge(humidity_df, on=['system:index'], how='left')
    final_df = final_df.merge(wind_df,on=['system:index'], how='left')
    final_df = final_df.merge(rainfall_df, on=['system:index'], how='left')
    final_df['impervious_percentage'] = isa_df['impervious_percentage'].values


    output_file = "Final_Merged_Dataset.csv"
    final_df.to_csv("Final_Merged_Dataset.csv",index=False)
    print("Final Dataset Merged !!!!")

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
