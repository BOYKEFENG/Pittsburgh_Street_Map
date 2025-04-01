import streamlit as st
from streamlit_folium import st_folium
import folium
import osmnx as ox
import networkx as nx
from shapely.geometry import Point
from shapely import wkt
import pandas as pd
import numpy as np
import requests

def display_preloaded_map(threshold, network_label="Network"):
    if "Bike" in network_label:
        prefix = "bike_slope_map_threshold_"
        folder = "bike_preloaded_maps"
    else:
        prefix = "slope_map_threshold_"
        folder = "preloaded_maps"

    map_url = f"https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/refs/heads/main/{folder}/{prefix}{int(threshold)}.html"
    response = requests.get(map_url)
    if response.status_code == 200:
        st.subheader(f"{network_label} Map for Absolute Slope ≤ {threshold}%")
        st.components.v1.html(response.text, height=500, scrolling=True)
    else:
        st.warning(f"Preloaded map for slope threshold {threshold}% not found. Please check the repository.")

def visualize_shortest_path_with_slope(start_location, end_location, threshold, network_label="Network"):
    try:
        if "Bike" in network_label:
            slope_url = f"https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/refs/heads/main/bike_slope_thresholds/pittsburgh_bike_slopes_threshold_{threshold}.csv"
        else:
            slope_url = f"https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/refs/heads/main/slope_thresholds/pittsburgh_street_slopes_threshold_{threshold}.csv"

        slope_data = pd.read_csv(slope_url, skip_blank_lines=True, header=0)
        slope_data.columns = [col.strip() for col in slope_data.columns]

        if 'geometry' in slope_data.columns:
            slope_data['geometry'] = slope_data['geometry'].apply(lambda x: wkt.loads(x) if pd.notnull(x) else None)

        filtered_slope_data = slope_data[slope_data['abs_slope_percentage'] <= threshold]
        if filtered_slope_data.empty:
            st.error("Filtered data is empty! No streets meet the slope threshold.")
            return None

        node_map = {}
        node_id_counter = 0

        def get_unique_node_id(lat, lon):
            nonlocal node_id_counter
            key = (lat, lon)
            if key not in node_map:
                node_map[key] = node_id_counter
                node_id_counter += 1
            return node_map[key]

        G = nx.MultiDiGraph()

        for _, row in filtered_slope_data.iterrows():
            u_id = get_unique_node_id(row['start_lat'], row['start_lon'])
            v_id = get_unique_node_id(row['end_lat'], row['end_lon'])

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

        if "Pittsburgh" not in start_location:
            start_location = f"{start_location}, Pittsburgh, PA"
        if "Pittsburgh" not in end_location:
            end_location = f"{end_location}, Pittsburgh, PA"

        start_point = ox.geocode(start_location)
        end_point = ox.geocode(end_location)

        def find_nearest_node(graph, target_point):
            target_geom = Point(target_point[1], target_point[0])
            distances = {node: target_geom.distance(Point(data['x'], data['y'])) for node, data in graph.nodes(data=True)}
            return min(distances, key=distances.get)

        start_node = find_nearest_node(G, start_point)
        end_node = find_nearest_node(G, end_point)

        if not nx.has_path(G, source=start_node, target=end_node):
            st.error("No valid path exists between the start and end locations with the given slope threshold.")
            return None

        path_length, shortest_path = nx.bidirectional_dijkstra(G, source=start_node, target=end_node, weight='length')
        st.write(f"Total path length: {path_length:.2f} meters")

        midpoint = [(start_point[0] + end_point[0]) / 2, (start_point[1] + end_point[1]) / 2]
        m = folium.Map(location=midpoint, zoom_start=13, tiles="CartoDB positron")

        for i in range(len(shortest_path) - 1):
            u = shortest_path[i]
            v = shortest_path[i + 1]
            edge_data = G.get_edge_data(u, v)
            selected_edge = min(edge_data.values(), key=lambda x: x.get('length', float('inf')))
            if 'geometry' in selected_edge and selected_edge['geometry'] is not None:
                coords = [(pt[1], pt[0]) for pt in selected_edge['geometry'].coords]
            else:
                coords = [(G.nodes[u]['y'], G.nodes[u]['x']), (G.nodes[v]['y'], G.nodes[v]['x'])]
            folium.PolyLine(coords, color="blue", weight=5, opacity=0.7).add_to(m)

        folium.Marker(location=start_point, icon=folium.Icon(color="green"), popup="Start").add_to(m)
        folium.Marker(location=end_point, icon=folium.Icon(color="red"), popup="End").add_to(m)

        return m

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

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
    
    network_type = st.sidebar.radio("Select Network Type", ["Vehicle Drive Network", "Bike Network"])
    if network_type == "Vehicle Drive Network":
        slope_prefix = "pittsburgh_street_slopes_threshold_"
        max_threshold = 40
        network_label = "Vehicle Drive Network"
    else:
        slope_prefix = "pittsburgh_bike_slopes_threshold_"
        max_threshold = 43
        network_label = "Bike Network"

    page = st.sidebar.radio("Select Feature", ["Preloaded Slope Maps", "Slope-Constrained Shortest Path Visualization"])

    if page == "Preloaded Slope Maps":
        st.subheader(f"{network_label} - Preloaded Slope Maps")
        threshold = st.sidebar.number_input("Slope Threshold (%)", min_value=1, max_value=max_threshold, value=5)
        if st.button("Display Preloaded Map"):
            display_preloaded_map(threshold, network_label)

    elif page == "Slope-Constrained Shortest Path Visualization":
        st.subheader(f"{network_label} - Slope-Constrained Shortest Path")
        st.write("Enter the start and end addresses, along with a slope threshold, to compute and visualize the shortest path.")
        start_location = st.text_input("Start Address:", "Carnegie Mellon University, Pittsburgh")
        end_location = st.text_input("End Address:", "6105 Spirit Street")
        threshold = st.number_input("Slope Threshold (%)", min_value=1, max_value=max_threshold, value=5)
        if st.button("Show Slope-Constrained Shortest Path"):
            with st.spinner("Calculating..."):
                path_map = visualize_shortest_path_with_slope(start_location, end_location, threshold, network_label)
                if path_map:
                    st_folium(path_map, width=700, height=500)

if __name__ == "__main__":
    main()
