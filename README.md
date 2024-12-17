# Pittsburgh Street Slope Visualization Project

This project analyzes and visualizes **street slopes** in **Pittsburgh, Pennsylvania** to determine the suitability of streets for truck navigation based on slope constraints. It uses **Python** for data processing and generates interactive maps for slope thresholds.

---

## **Project Overview**

### **Purpose**
- Analyze and visualize street slope data.
- Identify streets that meet slope constraints (e.g., slopes ≤ 10%) for safer truck navigation.
- Provide interactive maps for exploration.

### **Key Features**
1. **Street Network Data**: Download and process road networks from OpenStreetMap.
2. **Elevation Analysis**: Retrieve elevation data for street start and end points.
3. **Slope Calculation**: Calculate slope percentages for each road segment.
4. **Threshold Filtering**: Filter streets by slope thresholds (1% to 40%).
5. **Interactive Maps**: Visualize filtered streets on interactive Folium maps.

---

## **Data Workflow**

1. **Street Network Retrieval**:
   - Download the street network for Pittsburgh and save it as a GraphML file.

2. **Elevation Data**:
   - Retrieve elevation data for each street segment using the TessaDEM API.

3. **Slope Calculation**:
   - Calculate slopes:
     \[
     \text{Slope Percentage} = \frac{\text{Elevation Change}}{\text{Street Length}} \times 100
     \]

4. **Threshold Filtering**:
   - Generate slope-constrained datasets for thresholds from 1% to 40%.

5. **Map Visualization**:
   - Create interactive maps to display filtered streets for each threshold.

---

## **Project Structure**

```plaintext
Pittsburgh_Street_Map/
│
├── pittsburgh_street_network.png        # Overview of Pittsburgh's street network
├── pittsburgh_street_slopes.csv         # Original slope data
├── slope_thresholds/                    # Filtered slope data (1% - 40%)
│   ├── pittsburgh_street_slopes_threshold_1.csv
│   ├── pittsburgh_street_slopes_threshold_2.csv
│   ├── ... (continues up to threshold_40)
│
├── preloaded_maps/                      # HTML maps for thresholds
│   ├── slope_map_threshold_1.html
│   ├── slope_map_threshold_2.html
│   ├── ... (continues up to threshold_40)
│
├── Pitts_Map.py                         # Streamlit app to visualize preloaded maps
├── Pitts_Street_Slope.py                # Script to process slope data
├── requirements.txt                     # Python dependencies
└── README.md                            # Project documentation
