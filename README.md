# Pittsburgh Street Slope Visualization Project

This project analyzes and visualizes **street slopes** in **Pittsburgh, Pennsylvania** to identify truck-suitable streets under slope constraints. The workflow includes downloading road network data, retrieving elevation data, calculating slopes, and visualizing results using **interactive maps**.

---

## **Key Features**

1. **Street Network Data**:  
   Download and process road networks from OpenStreetMap.

2. **Elevation Analysis**:  
   Retrieve elevation data for street start and end points using the TessaDEM API.

3. **Slope Calculation**:  
   Calculate slope percentages for each road segment.

4. **Threshold Filtering**:  
   Generate slope-constrained datasets for thresholds ranging from 1% to 40%.

5. **Interactive Maps**:  
   Visualize filtered streets dynamically using Folium maps.

---

## **Data Workflow**

1. **Street Network Retrieval**:  
   - Download the street network for **Pittsburgh** and save it as a `GraphML` file using `osmnx`.

2. **Elevation Data**:  
   - Retrieve elevation data for start and end points of each street segment using the **TessaDEM API**.

3. **Slope Calculation**:  
   The slope percentage for each street segment is calculated as follows:

   **Slope Percentage** = (Elevation Change / Street Length) × 100


4. **Threshold Filtering**:  
   - Filter streets based on absolute slope percentages from **1% to 40%**.
   - Generate separate CSV files for each threshold.

5. **Map Visualization**:  
   - Create interactive **Folium maps** to visualize streets that meet slope constraints.

---

## **Project Structure**

The project repository is organized as follows:

```plaintext
Pittsburgh_Street_Map/
│
├── pittsburgh_street_network.png        # Overview chart of Pittsburgh's street network
├── pittsburgh_street_slopes.csv         # Original processed slope data
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



