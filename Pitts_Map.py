import streamlit as st
from streamlit_folium import st_folium
import folium
import osmnx as ox
import networkx as nx
from shapely.geometry import Point
from shapely import wkt
import pandas as pd
import requests
from io import StringIO

# ------------------------------
# Display Preloaded Map
# ------------------------------
def display_preloaded_map(threshold):
    # Construct GitHub URL for the preloaded map
    map_url = f"https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/main/preloaded_maps/slope_map_threshold_{int(threshold)}.html"
    
    response = requests.get(map_url)
    if response.status_code == 200:
        st.subheader(f"Map for Absolute Slope ≤ {threshold}%")
        html = response.text
        st.components.v1.html(html, height=500, scrolling=True)
    else:
        st.warning(f"Preloaded map for slope threshold {threshold}% not found. Please check your map repository.")

# ------------------------------
# Visualize Shortest Path with Slope Constraint
# ------------------------------
def visualize_shortest_path_with_slope(start_location, end_location, threshold):
    try:
        # GitHub URL for the slope data CSV
        slope_url = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/main/pittsburgh_street_slopes.csv"
        
        st.write("Loading street network graph from slope CSV...")
        response = requests.get(slope_url)
        response.raise_for_status()  # Raise exception for bad status codes
        slope_data = pd.read_csv(StringIO(response.text), skip_blank_lines=True, header=0)
        slope_data.columns = [col.strip() for col in slope_data.columns]

        if 'geometry' in slope_data.columns:
            slope_data['geometry'] = slope_data['geometry'].apply(wkt.loads)
        
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
            
            edge_attrs = {'length': row['length'], 'slope': row['abs_slope_percentage']}
            if 'geometry' in row and pd.notnull(row['geometry']):
                edge_attrs['geometry'] = row['geometry']
            G.add_edge(u_id, v_id, **edge_attrs)

        st.write("Graph successfully loaded and filtered by slope threshold.")

        # Geocoding with Pittsburgh context
        if "Pittsburgh" not in start_location:
            start_location += ", Pittsburgh, PA"
        if "Pittsburgh" not in end_location:
            end_location += ", Pittsburgh, PA"

        start_point = ox.geocode(start_location)
        end_point = ox.geocode(end_location)

        def find_nearest_node(graph, target_point):
            target_geom = Point(target_point[1], target_point[0])
            distances = {
                node: target_geom.distance(Point(data['x'], data['y']))
                for node, data in graph.nodes(data=True)
            }
            return min(distances, key=distances.get)

        start_node = find_nearest_node(G, start_point)
        end_node = find_nearest_node(G, end_point)

        st.write("Calculating the shortest path...")
        if not nx.has_path(G, source=start_node, target=end_node):
            st.error("No valid path exists with the given slope threshold.")
            return None

        shortest_path = nx.shortest_path(G, source=start_node, target=end_node, weight='length')

        midpoint = [(start_point[0] + end_point[0])/2, (start_point[1] + end_point[1])/2]
        m = folium.Map(location=midpoint, zoom_start=13, tiles="CartoDB positron")

        for i in range(len(shortest_path) - 1):
            u = shortest_path[i]
            v = shortest_path[i + 1]
            edge_data = G.get_edge_data(u, v)
            selected_edge = min(edge_data.values(), key=lambda x: x.get('length', float('inf')))
            
            if 'geometry' in selected_edge and selected_edge['geometry']:
                coords = [(pt[1], pt[0]) for pt in selected_edge['geometry'].coords]
            else:
                coords = [(G.nodes[u]['y'], G.nodes[u]['x']), (G.nodes[v]['y'], G.nodes[v]['x'])]
            
            folium.PolyLine(coords, color="blue", weight=5, opacity=0.7).add_to(m)

        folium.Marker(start_point, icon=folium.Icon(color="green"), popup="Start").add_to(m)
        folium.Marker(end_point, icon=folium.Icon(color="red"), popup="End").add_to(m)

        return m

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return None

# ------------------------------
# Streamlit App Layout
# ------------------------------
def main():
    st.set_page_config(page_title="Pittsburgh Truck Route Planner", layout="wide")
    st.title("Pittsburgh Truck-Suitable Street Segments Map")
    st.write("""
    Visualize Pittsburgh streets by slope threshold and find slope-constrained routes.
    """)

    page = st.sidebar.radio("Navigation", ["Preloaded Maps", "Route Planner"])

    if page == "Preloaded Maps":
        st.sidebar.header("Slope Threshold")
        slope_threshold = st.sidebar.number_input(
            "Slope percentage threshold (integer):", 
            min_value=1, max_value=40, value=5, step=1
        )

        if st.sidebar.button("Load Map"):
            st.session_state.selected_threshold = slope_threshold

        if 'selected_threshold' in st.session_state:
            display_preloaded_map(st.session_state.selected_threshold)
    
    elif page == "Route Planner":
        st.title("Slope-Constrained Route Planner")
        
        col1, col2 = st.columns(2)
        with col1:
            start_loc = st.text_input("Start Location:", "Carnegie Mellon University")
        with col2:
            end_loc = st.text_input("End Location:", "6105 Spirit Street")
        
        slope_threshold = st.number_input(
            "Maximum slope percentage:", 
            min_value=1, max_value=40, value=5, step=1
        )

        if st.button("Calculate Route"):
            with st.spinner("Finding optimal route..."):
                route_map = visualize_shortest_path_with_slope(start_loc, end_loc, slope_threshold)
                if route_map:
                    st.session_state['route_map'] = route_map
                else:
                    st.warning("Could not find a valid route. Try increasing the slope threshold.")

        if 'route_map' in st.session_state:
            st_folium(st.session_state['route_map'], width=700, height=500)

if __name__ == "__main__":
    main()
