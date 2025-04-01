import streamlit as st
from streamlit_folium import st_folium
import folium
import osmnx as ox
import networkx as nx
from shapely.geometry import Point
from shapely import wkt  # For converting WKT strings to geometry objects
import pandas as pd
import numpy as np
import requests

# ------------------------------
# Display Preloaded Map
# ------------------------------
def display_preloaded_map(threshold, map_folder, network_label="Network"):
    """
    Displays a preloaded Folium map for a given slope threshold.
    Uses different file-name prefixes depending on whether
    it's the Bike Network or Vehicle Drive Network.
    """
    # Decide prefix for the HTML file based on the network type
    if "Bike" in network_label:
        prefix = "bike_slope_map_threshold_"
    else:
        prefix = "slope_map_threshold_"

    # Construct the expected URL
    map_url = f"{map_folder}/{prefix}{int(threshold)}.html"

    response = requests.get(map_url)
    if response.status_code == 200:
        st.subheader(f"{network_label} Map for Absolute Slope ≤ {threshold}%")
        html = response.text
        st.components.v1.html(html, height=500, scrolling=True)
    else:
        st.warning(
            f"Preloaded map for slope threshold {threshold}% not found at {map_folder}.\n"
            f"Expected URL: {map_url}"
        )

# ------------------------------
# Visualize Shortest Path with Slope Constraint
# ------------------------------
def visualize_shortest_path_with_slope(
    start_location,
    end_location,
    threshold,
    slope_file,
    network_label="Network"
):
    """
    Loads the specified threshold-based slope CSV, filters edges by threshold,
    and then computes the shortest path from start_location to end_location.
    Returns a Folium map if successful, or None if an error occurs.
    """
    try:
        st.write(f"Loading {network_label} street network graph from slope CSV:")
        st.write(f"  -> {slope_file}")

        slope_data = pd.read_csv(slope_file, skip_blank_lines=True, header=0)
        slope_data.columns = [col.strip() for col in slope_data.columns]  # Clean column names

        # If geometry column exists, convert from WKT to shapely geometry
        if 'geometry' in slope_data.columns:
            slope_data['geometry'] = slope_data['geometry'].apply(wkt.loads)

        # Filter the slope data by threshold
        filtered_slope_data = slope_data[slope_data['abs_slope_percentage'] <= threshold]
        if filtered_slope_data.empty:
            st.error("Filtered data is empty! No streets meet the slope threshold.")
            return None

        # Assign unique IDs to nodes based on their coordinates
        node_map = {}
        node_id_counter = 0

        def get_unique_node_id(lat, lon):
            nonlocal node_id_counter
            key = (lat, lon)
            if key not in node_map:
                node_map[key] = node_id_counter
                node_id_counter += 1
            return node_map[key]

        # Initialize graph
        G = nx.MultiDiGraph()

        # Add edges to the graph and include geometry if available
        for _, row in filtered_slope_data.iterrows():
            u_id = get_unique_node_id(row['start_lat'], row['start_lon'])
            v_id = get_unique_node_id(row['end_lat'], row['end_lon'])

            # Add nodes if they are not already present
            if u_id not in G.nodes:
                G.add_node(u_id, y=row['start_lat'], x=row['start_lon'])
            if v_id not in G.nodes:
                G.add_node(v_id, y=row['end_lat'], x=row['end_lon'])

            edge_attrs = {
                'length': row['length'],
                'slope': row['abs_slope_percentage']
            }
            if 'geometry' in row and pd.notnull(row['geometry']):
                edge_attrs['geometry'] = row['geometry']

            G.add_edge(u_id, v_id, **edge_attrs)

        st.write(f"{network_label} graph loaded and filtered by slope threshold {threshold}%.")

        # Improve geocoding by appending Pittsburgh if missing
        if "Pittsburgh" not in start_location:
            start_location = f"{start_location}, Pittsburgh, PA"
        if "Pittsburgh" not in end_location:
            end_location = f"{end_location}, Pittsburgh, PA"

        start_point = ox.geocode(start_location)
        end_point = ox.geocode(end_location)

        # Find the nearest nodes in the graph based on Euclidean distance
        def find_nearest_node(graph, target_point):
            target_geom = Point(target_point[1], target_point[0])
            distances = {
                node: target_geom.distance(Point(data['x'], data['y']))
                for node, data in graph.nodes(data=True)
            }
            return min(distances, key=distances.get)

        start_node = find_nearest_node(G, start_point)
        end_node = find_nearest_node(G, end_point)

        st.write("Calculating the shortest path using bidirectional Dijkstra's algorithm...")
        if not nx.has_path(G, source=start_node, target=end_node):
            st.error("No valid path exists between the start and end locations with the given slope threshold.")
            return None

        # Calculate shortest path using bidirectional Dijkstra's algorithm (returns total length and path)
        path_length, shortest_path = nx.bidirectional_dijkstra(G, source=start_node, target=end_node, weight='length')
        
        # Display the total path length
        st.write(f"Total path length: {path_length:.2f} meters")

        # Plot the path on a Folium map using full edge geometries
        midpoint = [(start_point[0] + end_point[0]) / 2, (start_point[1] + end_point[1]) / 2]
        m = folium.Map(location=midpoint, zoom_start=13, tiles="CartoDB positron")

        # For each consecutive node pair, use detailed geometry if available
        for i in range(len(shortest_path) - 1):
            u = shortest_path[i]
            v = shortest_path[i + 1]
            edge_data = G.get_edge_data(u, v)
            # If multiple edges exist, choose the one with the smallest length
            selected_edge = min(edge_data.values(), key=lambda x: x.get('length', float('inf')))

            if 'geometry' in selected_edge and selected_edge['geometry'] is not None:
                # Convert (lon, lat) to (lat, lon) for Folium
                coords = [(pt[1], pt[0]) for pt in selected_edge['geometry'].coords]
            else:
                coords = [
                    (G.nodes[u]['y'], G.nodes[u]['x']),
                    (G.nodes[v]['y'], G.nodes[v]['x'])
                ]

            folium.PolyLine(coords, color="blue", weight=5, opacity=0.7).add_to(m)

        # Add markers for start and end points
        folium.Marker(location=start_point, icon=folium.Icon(color="green"), popup="Start").add_to(m)
        folium.Marker(location=end_point, icon=folium.Icon(color="red"), popup="End").add_to(m)

        return m

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# ------------------------------
# Streamlit App Layout
# ------------------------------
def main():
    st.set_page_config(page_title="Pittsburgh Slope-Sensitive(S2) Street Map", layout="wide")
    st.title("Pittsburgh Slope-Sensitive(S2) Street Map")
    st.write("""
    This application allows you to input a slope threshold percentage and directly displays the preloaded map for that threshold.
    It also lets you visualize the shortest path between two locations in Pittsburgh that satisfies the given slope constraint.
    """)
    st.markdown("""  
    **Slope Percentage** = (Elevation Change / Street Length) × 100  
    - **1% slope** is approximately **0.573 degrees**.  
    - **1 degree** corresponds to approximately **1.75% slope**.  
    """, unsafe_allow_html=True)
    
    # 1. Select Network Type
    network_type = st.sidebar.radio(
        "Select Network Type",
        ["Vehicle Drive Network", "Bike Network"]
    )

    # Set file paths & naming logic based on network type
    if network_type == "Vehicle Drive Network":
        preloaded_map_folder = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/refs/heads/main/preloaded_maps"
        slope_threshold_folder = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/refs/heads/main/slope_thresholds"
        slope_csv_prefix = "pittsburgh_street_slopes_threshold_"
        network_label = "Vehicle Drive Network"
        max_threshold_value = 40
    else:
        preloaded_map_folder = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/refs/heads/main/bike_preloaded_maps"
        slope_threshold_folder = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/refs/heads/main/bike_slope_thresholds"
        slope_csv_prefix = "pittsburgh_bike_slopes_threshold_"
        network_label = "Bike Network"
        max_threshold_value = 43

    # 3. Page/Feature Selection
    page = st.sidebar.radio(
        "Select Feature",
        ["Preloaded Slope Maps", "Slope-Constrained Shortest Path Visualization"]
    )

    # 3A. Preloaded Slope Maps
    if page == "Preloaded Slope Maps":
        st.subheader(f"{network_label} - Preloaded Slope Maps")
        slope_threshold = st.sidebar.number_input(
            f"Enter the slope threshold percentage (1-{max_threshold_value})", 
            min_value=1, 
            max_value=max_threshold_value, 
            value=5, 
            step=1
        )
        # Button to display the preloaded map
        if st.button("Display Preloaded Map"):
            display_preloaded_map(
                threshold=slope_threshold,
                map_folder=preloaded_map_folder,
                network_label=network_label
            )

    # 3B. Slope-Constrained Shortest Path Visualization
    elif page == "Slope-Constrained Shortest Path Visualization":
        st.subheader(f"{network_label} - Slope-Constrained Shortest Path")
        st.write("Enter the start and end addresses, along with a slope threshold, to compute and visualize the shortest path.")

        # User input for start and end locations
        start_location = st.text_input(
            "Enter Start Address or Location Name:", 
            "Carnegie Mellon University, Pittsburgh", 
            key="start"
        )
        end_location = st.text_input(
            "Enter End Address or Location Name:", 
            "6105 Spirit Street", 
            key="end"
        )

        # User input for slope threshold
        slope_threshold = st.number_input(
            f"Enter the slope threshold percentage (1-{max_threshold_value}):", 
            min_value=1, 
            max_value=max_threshold_value, 
            value=5, 
            step=1
        )

        # Construct the threshold-based CSV URL
        slope_file = f"{slope_threshold_folder}/{slope_csv_prefix}{slope_threshold}.csv"

        # Button to compute and display the slope-constrained shortest path
        if st.button("Show Slope-Constrained Shortest Path"):
            if start_location and end_location and slope_threshold:
                with st.spinner(f"Calculating the shortest path in {network_label}..."):
                    shortest_path_map = visualize_shortest_path_with_slope(
                        start_location=start_location,
                        end_location=end_location,
                        threshold=slope_threshold,
                        slope_file=slope_file,
                        network_label=network_label
                    )
                    if shortest_path_map:
                        st.session_state['shortest_path_with_slope'] = shortest_path_map
                        st.success("Path successfully generated.")
                    else:
                        st.error("Failed to generate the path. No valid path exists or check your slope data.")

        # Display the map if it exists in the session state
        if 'shortest_path_with_slope' in st.session_state:
            st_folium(st.session_state['shortest_path_with_slope'], width=700, height=500)

if __name__ == "__main__":
    main()
