import pandas as pd
import os
import requests

# Input file URL for the original slope data CSV from GitHub
input_csv_url = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/main/pittsburgh_street_slopes.csv"

# Local file path to store the downloaded input CSV
input_csv_path = "pittsburgh_street_slopes.csv"

# Output folder where filtered files will be saved
output_folder = "slope_thresholds"

# Download the input CSV file from GitHub
if not os.path.exists(input_csv_path):
    print("Downloading the input CSV file from GitHub...")
    response = requests.get(input_csv_url)
    if response.status_code == 200:
        with open(input_csv_path, "wb") as file:
            file.write(response.content)
        print(f"Input CSV file downloaded successfully to {input_csv_path}")
    else:
        raise Exception(f"Failed to download input CSV. HTTP Status Code: {response.status_code}")

# Create the output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Load the data
slope_data = pd.read_csv(input_csv_path)

# Generate separate files for absolute slope thresholds from 1 to 40
for threshold in range(1, 41):
    # Filter the data for the given threshold
    filtered_data = slope_data[slope_data['abs_slope_percentage'] <= threshold]
    
    # Define the output file path
    output_file_path = os.path.join(output_folder, f'pittsburgh_street_slopes_threshold_{threshold}.csv')
    
    # Save the filtered data to a new CSV
    filtered_data.to_csv(output_file_path, index=False)

print(f"Generated files for slope thresholds 1 to 40 in the folder: {output_folder}")
