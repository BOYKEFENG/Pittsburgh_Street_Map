import os
import pandas as pd
import folium
from shapely.wkt import loads as wkt_loads

# ------------------------------
# Load Slope Data
# ------------------------------
def load_data(csv_path):
    try:
        data = pd.read_csv(csv_path)
        # Convert WKT geometry strings to shapely LineString objects
        data['geometry'] = data['geometry'].apply(wkt_loads)
        return data
    except FileNotFoundError:
        print(f"CSV file not found at path: {csv_path}")
        return pd.DataFrame()

# ------------------------------
# Create Folium Map
# ------------------------------
def create_map(filtered_data, center_lat=40.4406, center_lon=-79.9959, zoom_start=12):
    # Initialize Folium map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start, tiles='CartoDB positron')

    # Define a color scale based on absolute slope_percentage
    min_slope = filtered_data['abs_slope_percentage'].min()
    max_slope = filtered_data['abs_slope_percentage'].max()

    # Handle case where min_slope == max_slope to prevent division by zero
    if min_slope == max_slope:
        min_slope -= 1
        max_slope += 1

    colormap = folium.LinearColormap(['green', 'yellow', 'red'], vmin=min_slope, vmax=max_slope)
    colormap.caption = 'Absolute Slope Percentage (%)'
    colormap.add_to(m)

    # Add street segments to the map using their actual geometry
    for idx, row in filtered_data.iterrows():
        color = colormap(row['abs_slope_percentage'])
        folium.PolyLine(
            locations=[(lat, lon) for lon, lat in row['geometry'].coords],  # Extract coordinates from LineString
            color=color,
            weight=5,
            opacity=0.7,
            tooltip=f"ID: {row['osmid']}<br>Slope: {row['slope_percentage']:.2f}%<br>Street: {row['street_name']}"
        ).add_to(m)
    
    return m

# ------------------------------
# Generate and Save Maps
# ------------------------------
def generate_maps(data_folder, output_folder, thresholds=range(1, 41)):
    os.makedirs(output_folder, exist_ok=True)  # Ensure output folder exists

    for threshold in thresholds:
        print(f"Processing map for slope threshold: {threshold}%...")
        
        # Path to the preprocessed CSV file
        csv_path = os.path.join(data_folder, f"pittsburgh_street_slopes_threshold_{threshold}.csv")
        
        if not os.path.exists(csv_path):
            print(f"File for threshold {threshold}% not found. Skipping...")
            continue

        # Load data
        data = load_data(csv_path)
        if data.empty:
            print(f"No data found for threshold {threshold}%. Skipping...")
            continue

        # Create map
        folium_map = create_map(data)

        # Save map as an HTML file
        output_file = os.path.join(output_folder, f"slope_map_threshold_{threshold}.html")
        folium_map.save(output_file)
        print(f"Map for threshold {threshold}% saved to {output_file}")

    print("All maps generated and saved.")

# ------------------------------
# Main Execution
# ------------------------------
if __name__ == "__main__":
    # Path to folder containing preprocessed slope data
    data_folder = r'C:\Users\fengy\OneDrive\Desktop\24FALL\Pitts_Street_Bridge_Data\slope_thresholds'
    
    # Path to folder where maps will be saved
    output_folder = r'C:\Users\fengy\OneDrive\Desktop\24FALL\Pitts_Street_Bridge_Data\preloaded_maps'

    # Generate maps for thresholds from 1 to 40
    generate_maps(data_folder, output_folder, thresholds=range(1, 41))
