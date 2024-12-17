import streamlit as st
from streamlit_folium import st_folium
import os
import folium
import osmnx as ox
import networkx as nx
from shapely.geometry import Point
import pandas as pd
import numpy as np
import requests

# ------------------------------
# Display Preloaded Map
# ------------------------------
def display_preloaded_map(threshold, map_folder):
    map_file = f"https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/main/preloaded_maps/slope_map_threshold_{int(threshold)}.html"

    response = requests.get(map_file)
    if response.status_code == 200:
        st.subheader(f"Map for Absolute Slope ≤ {threshold}%")
        st.components.v1.html(response.text, height=500, scrolling=True)
    else:
        st.warning(f"Preloaded map for slope threshold {threshold}% not found. Please check your repository.")

# ------------------------------
# Visualize Shortest Path with Slope Constraint
# ------------------------------
def visualize_shortest_path_with_slope(start_location, end_location, threshold, slope_data_folder):
    try:
        # Load the slope data directly from CSV
        st.write("Loading street network graph from slope CSV...")
        slope_file = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/main/pittsburgh_street_slopes.csv"
        slope_data = pd.read_csv(slope_file, skip_blank_lines=True, header=0)
        slope_data.columns = [col.strip() for col in slope_data.columns]  # Clean column names

        # Filter the slope data
        filtered_slope_data = slope_data[slope_data['abs_slope_percentage'] <= threshold]
        if filtered_slope_data.empty:
            st.error("Filtered data is empty! No streets meet the slope threshold.")
            return None

        # Assign unique IDs to start and end nodes
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

        # Add edges with unique node IDs
        for _, row in filtered_slope_data.iterrows():
            u_id = get_unique_node_id(row['start_lat'], row['start_lon'])
            v_id = get_unique_node_id(row['end_lat'], row['end_lon'])

            G.add_node(u_id, y=row['start_lat'], x=row['start_lon'])
            G.add_node(v_id, y=row['end_lat'], x=row['end_lon'])
            G.add_edge(u_id, v_id, length=row['length'], slope=row['abs_slope_percentage'])

        st.write("Graph successfully loaded and filtered by slope threshold.")

        # Geocode start and end locations
        start_point = ox.geocode(start_location)
        end_point = ox.geocode(end_location)

        # Find the nearest nodes in the graph
        def find_nearest_node(graph, target_point):
            target_geom = Point(target_point[1], target_point[0])
            distances = {
                node: target_geom.distance(Point(data['x'], data['y']))
                for node, data in graph.nodes(data=True)
            }
            return min(distances, key=distances.get)

        start_node = find_nearest_node(G, start_point)
        end_node = find_nearest_node(G, end_point)

        # Check if a path exists
        st.write("Calculating the shortest path...")
        if not nx.has_path(G, source=start_node, target=end_node):
            st.error("No valid path exists between the start and end locations with the given slope threshold.")
            return None

        # Calculate shortest path
        shortest_path = nx.shortest_path(G, source=start_node, target=end_node, weight='length')

        # Plot the path on a Folium map
        midpoint = [(start_point[0] + end_point[0]) / 2, (start_point[1] + end_point[1]) / 2]
        m = folium.Map(location=midpoint, zoom_start=13, tiles="CartoDB positron")

        path_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in shortest_path]
        folium.PolyLine(path_coords, color="blue", weight=5, opacity=0.7).add_to(m)

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
    st.set_page_config(page_title="Pittsburgh Slope-Sensitive Street Segments Map", layout="wide")
    st.title("Pittsburgh Slope-Sensitive Street Segments Map")
    st.write("""
    This application allows you to input a slope threshold percentage and directly displays the preloaded map for that threshold. The maps are pre-generated to improve performance.
    """)

    # Sidebar Navigation
    page = st.sidebar.radio("Select Page", ["Preloaded Slope Maps", "Slope-Constrained Shortest Path Visualization"])

    if page == "Preloaded Slope Maps":
        # Sidebar for slope threshold input
        st.sidebar.header("Slope Threshold Input")
        slope_threshold = st.sidebar.number_input(
            "Enter the slope threshold percentage (integer values only)", 
            min_value=1, 
            max_value=40, 
            value=5, 
            step=1
        )

        # Add a button to apply changes
        if 'selected_threshold' not in st.session_state:
            st.session_state.selected_threshold = slope_threshold  # Default value

        apply_changes = st.sidebar.button("Apply Changes")

        if apply_changes:
            st.session_state.selected_threshold = slope_threshold

        # Path to the folder containing preloaded map files
        preloaded_map_folder = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/main/preloaded_maps"

        # Display the preloaded map using the stored threshold in session state
        display_preloaded_map(st.session_state.selected_threshold, preloaded_map_folder)
    
    elif page == "Slope-Constrained Shortest Path Visualization":
        st.title("Visualize Shortest Path with Slope Constraint")
        st.write("Input the start and end addresses, along with a slope threshold, to compute and visualize the shortest path in Pittsburgh's street network that satisfies the slope constraint.")

        # User input for start and end locations
        start_location = st.text_input("Enter Start Address or Location Name:", "Carnegie Mellon University, Pittsburgh", key="start")
        end_location = st.text_input("Enter End Address or Location Name:", "6105 Spirit Street", key="end")

        # User input for slope threshold
        slope_threshold = st.number_input(
            "Enter the slope threshold percentage:", 
            min_value=1, max_value=40, value=5, step=1
        )

        # Button to compute and display the slope-constrained shortest path
        slope_data_folder = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/main/slope_thresholds"
        if st.button("Show Slope-Constrained Shortest Path"):
            if start_location and end_location and slope_threshold:
                with st.spinner("Calculating the shortest path with slope constraint..."):
                    shortest_path_map = visualize_shortest_path_with_slope(
                        start_location, end_location, slope_threshold, slope_data_folder
                    )
                    if shortest_path_map:
                        st.session_state['shortest_path_with_slope'] = shortest_path_map
                    else:
                        st.warning("Failed to generate the map. Check the input locations or slope data.")

        # Display the map if it exists in the session state
        if 'shortest_path_with_slope' in st.session_state:
            st_folium(st.session_state['shortest_path_with_slope'], width=700, height=500)

if __name__ == "__main__":
    main()
