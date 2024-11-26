import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from shapely.wkt import loads as wkt_loads

# ------------------------------
# Load Slope Data
# ------------------------------
@st.cache_data
def load_data(csv_path):
    try:
        data = pd.read_csv(csv_path)
        # Convert WKT geometry strings to shapely LineString objects
        data['geometry'] = data['geometry'].apply(wkt_loads)
        return data
    except FileNotFoundError:
        st.error(f"CSV file not found at path: {csv_path}")
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
# Display Map Based on Threshold
# ------------------------------
def display_map(data, slope_threshold):
    # Filter data based on absolute slope threshold
    filtered_data = data[data['abs_slope_percentage'] <= slope_threshold].copy()

    st.subheader(f"Street Segments with Absolute Slope ≤ {slope_threshold}%")
    st.write(f"Number of suitable segments: {filtered_data.shape[0]}")

    if not filtered_data.empty:
        # Display a snippet of the filtered data
        st.dataframe(filtered_data[['osmid', 'street_name', 'slope_percentage', 'abs_slope_percentage']].head())

        # Create and display the map
        folium_map = create_map(filtered_data)
        st_map = st_folium(folium_map, width=700, height=500)

        # Optional: Provide a download button for the filtered data
        csv = filtered_data.to_csv(index=False)
        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv,
            file_name='suitable_street_segments.csv',
            mime='text/csv',
        )
    else:
        st.info("No street segments meet the specified slope threshold.")

# ------------------------------
# Streamlit App Layout
# ------------------------------
def main():
    st.set_page_config(page_title="Pittsburgh Truck-Suitable Street Segments Map", layout="wide")
    st.title("Pittsburgh Truck-Suitable Street Segments Map")
    st.write("""
    This application allows you to input a slope threshold percentage. It then filters and displays all street segments in Pittsburgh that have an **absolute slope less than or equal to** the specified threshold. These segments are suitable for truck traversal based on the slope criteria.
    """)

    # Sidebar for user input
    st.sidebar.header("Slope Threshold Input")
    slope_threshold = st.sidebar.number_input(
        "Enter the slope threshold percentage (%)", 
        min_value=0.0, 
        max_value=20.0, 
        value=5.0, 
        step=0.1
    )

    # Define the path to the CSV file
    csv_path = r'C:\Users\fengy\OneDrive\Desktop\24FALL\Pitts_Street_Bridge_Data\pittsburgh_street_slopes.csv'

    # Load data
    data = load_data(csv_path)

    if data.empty:
        st.warning("No data available to display. Please ensure the CSV file is generated correctly.")
        return

    # Handle missing street names by filling NaN with 'Unnamed Street'
    data['street_name'].fillna('Unnamed Street', inplace=True)

    # Display the map based on the selected threshold
    display_map(data, slope_threshold)

if __name__ == "__main__":
    main()
