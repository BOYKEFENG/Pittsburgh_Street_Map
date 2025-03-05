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

# ------------------------------
# Caching Functions
# ------------------------------
@st.cache_data(show_spinner=False)
def get_preloaded_map_html(map_url):
    response = requests.get(map_url)
    if response.status_code == 200:
        return response.text
    return None

@st.cache_data(show_spinner=False)
def load_slope_data(slope_url):
    slope_data = pd.read_csv(slope_url, skip_blank_lines=True, header=0)
    slope_data.columns = [col.strip() for col in slope_data.columns]
    if 'geometry' in slope_data.columns:
        slope_data['geometry'] = slope_data['geometry'].apply(lambda x: wkt.loads(x) if pd.notnull(x) else None)
    return slope_data

# ------------------------------
# Display Preloaded Map
# ------------------------------
def display_preloaded_map(threshold):
    # Use the GitHub URL for the preloaded map file
    map_url = f"https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/main/preloaded_maps/slope_map_threshold_{int(threshold)}.html"
    html = get_preloaded_map_html(map_url)
    if html:
        st.subheader(f"Map for Absolute Slope ≤ {threshold}%")
        st.markdown("""  
        **Slope Percentage** = (Elevation Change / Street Length) × 100  
        - **1% slope** is approximately **0.573 degrees**.  
        - **1 degree** corresponds to approximately **1.75% slope**.  
        """, unsafe_allow_html=True)
        st.components.v1.html(html, height=500, scrolling=True)
    else:
        st.warning(f"Preloaded map for slope threshold {threshold}% not found. Please check your repository.")

# ------------------------------
# Visualize Shortest Path with Slope Constraint
# ------------------------------
@st.cache_data(show_spinner=True)
def compute_shortest_path(start_location, end_location, threshold):
    # Load slope data from GitHub
    slope_url = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/main/pittsburgh_street_slopes.csv"
    slope_data = load_slope_data(slope_url)
    filtered_slope_data = slope_data[slope_data['abs_slope_percentage'] <= threshold]
    if filtered_slope_data.empty:
        return None, "Filtered data is empty! No streets meet the slope threshold."

    # Build graph from slope data
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
        edge_attrs = {'length': row['length'], 'slope': row['abs_slope_percentage']}
        if 'geometry' in row and pd.notnull(row['geometry']):
            edge_attrs['geometry'] = row['geometry']
        G.add_edge(u_id, v_id, **edge_attrs)

    # Append Pittsburgh context if missing
    if "Pittsburgh" not in start_location:
        start_location = f"{start_location}, Pittsburgh, PA"
    if "Pittsburgh" not in end_location:
        end_location = f"{end_location}, Pittsburgh, PA"

    # Geocode addresses using OSMnx
    start_point = ox.geocode(start_location)
    end_point = ox.geocode(end_location)

    def find_nearest_node(graph, target_point):
        target_geom = Point(target_point[1], target_point[0])
        distances = {node: target_geom.distance(Point(data['x'], data['y']))
                     for node, data in graph.nodes(data=True)}
        return min(distances, key=distances.get)

    start_node = find_nearest_node(G, start_point)
    end_node = find_nearest_node(G, end_point)

    if not nx.has_path(G, source=start_node, target=end_node):
        return None, "No valid path exists between the start and end locations with the given slope threshold."

    shortest_path = nx.shortest_path(G, source=start_node, target=end_node, weight='length')

    # Create a Folium map
    midpoint = [(start_point[0] + end_point[0]) / 2, (start_point[1] + end_point[1]) / 2]
    m = folium.Map(location=midpoint, zoom_start=13, tiles="CartoDB positron")

    # Draw each edge of the shortest path
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

    # Add markers
    folium.Marker(location=start_point, icon=folium.Icon(color="green"), popup="Start").add_to(m)
    folium.Marker(location=end_point, icon=folium.Icon(color="red"), popup="End").add_to(m)

    return m, None

def visualize_shortest_path_with_slope(start_location, end_location, threshold, slope_data_folder):
    m, error = compute_shortest_path(start_location, end_location, threshold)
    if error:
        st.error(error)
        return None
    return m

# ------------------------------
# Streamlit App Layout
# ------------------------------
def main():
    st.set_page_config(page_title="Pittsburgh Slope-Sensitive Street Segments Map", layout="wide")
    st.title("Pittsburgh Slope-Sensitive Street Segments Map")
    st.write("""
    This application allows you to input a slope threshold percentage and directly displays the preloaded map for that threshold.
    It also lets you visualize the shortest path between two locations in Pittsburgh that satisfies the given slope constraint.
    """)

    # Sidebar Navigation
    page = st.sidebar.radio("Select Page", ["Preloaded Slope Maps", "Slope-Constrained Shortest Path Visualization"])

    if page == "Preloaded Slope Maps":
        st.sidebar.header("Slope Threshold Input")
        slope_threshold = st.sidebar.number_input("Enter the slope threshold percentage (integer values only)",
                                                  min_value=1, max_value=40, value=5, step=1)
        st.session_state.selected_threshold = slope_threshold
        display_preloaded_map(st.session_state.selected_threshold)

    elif page == "Slope-Constrained Shortest Path Visualization":
        st.title("Visualize Slope-Constrained Shortest Path")
        st.write("Input the start and end addresses, along with a slope threshold, to compute and visualize the shortest path in Pittsburgh's street network that satisfies the slope constraint.")
        st.markdown("""  
        **Slope Percentage** = (Elevation Change / Street Length) × 100  
        - **1% slope** is approximately **0.573 degrees**.  
        - **1 degree** corresponds to approximately **1.75% slope**.  
        """, unsafe_allow_html=True)
        start_location = st.text_input("Enter Start Address or Location Name:",
                                       "Carnegie Mellon University, Pittsburgh", key="start")
        end_location = st.text_input("Enter End Address or Location Name:",
                                     "6105 Spirit Street", key="end")
        slope_threshold = st.number_input("Enter the slope threshold percentage (integer values only):",
                                          min_value=1, max_value=40, value=5, step=1)
        slope_data_folder = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/main/slope_thresholds"

        if st.button("Show Slope-Constrained Shortest Path"):
            if start_location and end_location and slope_threshold:
                with st.spinner("Calculating the shortest path with slope constraint..."):
                    shortest_path_map = visualize_shortest_path_with_slope(start_location, end_location, slope_threshold, slope_data_folder)
                    if shortest_path_map:
                        st.session_state['shortest_path_with_slope'] = shortest_path_map
                    else:
                        st.warning("Failed to generate the map. Check the input locations or slope data.")

        if 'shortest_path_with_slope' in st.session_state:
            st_folium(st.session_state['shortest_path_with_slope'], width=700, height=500, key="unique_map_key")

if __name__ == "__main__":
    main()
