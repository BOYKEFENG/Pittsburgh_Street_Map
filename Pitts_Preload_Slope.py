import pandas as pd
import os

# Input file path for the original slope data CSV
input_csv_path = r'C:\Users\fengy\OneDrive\Desktop\24FALL\Pitts_Street_Bridge_Data\pittsburgh_street_slopes.csv'

# Output folder where filtered files will be saved
output_folder = r'C:\Users\fengy\OneDrive\Desktop\24FALL\Pitts_Street_Bridge_Data\slope_thresholds'

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
