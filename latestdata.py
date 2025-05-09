import pandas as pd

# Load the dataset into a DataFrame
df = pd.read_csv("Final_Merged_Dataset_with_UHI_Labels.csv", index_col=0)

# Extract the unique dates from the 'Date' column
unique_dates = df['Date'].unique()

# Sort the dates and get the latest date
latest_date = sorted(unique_dates)[-1]

# Convert the latest date to string format 'YYYYMMDD'
latest_date_str = pd.to_datetime(latest_date).strftime('%Y%m%d')

# Generate expected indices for that date
expected_indices = [f"{latest_date_str}_{i}" for i in range(440)]

# Filter the DataFrame for these indices
filtered_df = df.loc[df.index.intersection(expected_indices)]

# Save the filtered data to CSV
filtered_df.to_csv("latest_data.csv", index=True)

print("CSV file 'latest_data.csv' created successfully.")
