from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np


def clustering_kmeans():
    df = pd.read_csv('Final_Merged_Dataset.csv')
    # Drop rows with missing values or interpolate
    df = df.replace(-999, np.nan)
    # Select relevant columns for clustering
    features = df[['LST_Celsius', 'NDVI', 'Air_Temperature_C', 'Dew_Point_Temperature_C',
                'Relative_Humidity_%', 'WindDirection', 'WindSpeed', 'Rainfall_mm', 'impervious_percentage']]
    df[features.columns] = df[features.columns].fillna(df[features.columns].mean())
    # Scale the features
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)
    df[features.columns] = scaled_features
    df[features.columns] = df[features.columns].replace(-999, np.nan)
    # Replace placeholder values like -999 with actual NaNs
    df[features.columns] = df[features.columns].replace(-999, np.nan)

    # Ensure all data is numeric (converts strings like 'NaN' to actual NaN)
    df[features.columns] = df[features.columns].apply(pd.to_numeric, errors='coerce')

    # Replace NaNs with mean of each column
    df[features.columns] = df[features.columns].fillna(df[features.columns].mean())

    from sklearn.cluster import KMeans

    # Choose number of clusters (we can optimize this later)
    k = 5  # Start with 5, can use elbow method to find optimal k

    # Perform clustering
    kmeans = KMeans(n_clusters=k, random_state=42)
    df['Cluster'] = kmeans.fit_predict(df[features.columns])
    cluster_summary = df.groupby('Cluster')[features.columns].mean().sort_values(by='LST_Celsius', ascending=False)

    # Sort the cluster summary by LST_Celsius in descending order
    sorted_clusters = cluster_summary.sort_values(by='LST_Celsius', ascending=False)
    # Create labels based on the sorted order
    uh_labels = ['High UHI', 'Moderate-High UHI', 'Moderate UHI', 'Low-Moderate UHI', 'Low UHI']

    # Map the clusters to labels based on sorted LST
    dynamic_cluster_labels = {sorted_clusters.index[i]: uh_labels[i] for i in range(len(sorted_clusters))}

    # Apply the dynamic mapping to the DataFrame
    df['UHI_Label'] = df['Cluster'].map(dynamic_cluster_labels)
    # Verify the result
    print(df[['Cluster', 'UHI_Label']].value_counts())
    temp_df = df[['Cluster', 'UHI_Label']].value_counts()
    # Save the cluster summary to a CSV file
    temp_df.to_csv('Cluster_Summary.csv')

    original_df = pd.read_csv('Final_Merged_Dataset.csv')
    # Merge the original DataFrame with the clustering results
    original_df['Cluster'] = df['Cluster']
    original_df['UHI_Label'] = df['UHI_Label']
    # Save the merged DataFrame to a new CSV file
    original_df.to_csv('Final_Merged_Dataset_with_UHI_Labels.csv', index=False)

    print("Clustering completed and saved to Final_Merged_Dataset_with_UHI_Labels.csv")