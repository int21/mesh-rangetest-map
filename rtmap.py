import os
import glob
import pandas as pd
import folium
import matplotlib.colors as mcolors
from folium.plugins import MeasureControl
from folium.plugins import Fullscreen
from folium.plugins import MousePosition
from folium.plugins import HeatMap

def create_point_layer(csv_file):

    df = pd.read_csv(csv_file)

    # Row filtering
    df_filtered = df[df['payload'].str.contains(r'seq \d+', na=False)]
    df_filtered = df_filtered[['rx lat', 'rx long', 'rx snr', 'sender name', 'rx elevation']].dropna()
    df_filtered = df_filtered[(df_filtered['rx lat'].apply(lambda x: isinstance(x, (int, float)))) &
                              (df_filtered['rx long'].apply(lambda x: isinstance(x, (int, float)))) &
                              (df_filtered['rx lat'].between(-90, 90)) &
                              (df_filtered['rx long'].between(-180, 180))]

    # Check if df_filtered has valid data
    if df_filtered.empty:
        print(f"No valid data found in {csv_file}. Skipping point layer creation.")
        return None

    # Create a FeatureGroup for the CSV file
    layer = folium.FeatureGroup(name=os.path.basename(csv_file))

    # Define the color map (from red to green)
    cmap = mcolors.LinearSegmentedColormap.from_list("", ["red", "yellow", "green"])

    # Normalize the SNR values to a range for color mapping
    df_filtered['normalized_snr'] = df_filtered['rx snr'].apply(lambda x: (x - (-21)) / (12 - (-21)))  # Normalize to range [-21, 12]

    # Add a marker for each point
    for _, row in df_filtered.iterrows():
        # Set color based on SNR
        if row['rx snr'] > 15 or row['rx snr'] <= -25:
            color = '#808080'  # Grey for SNR > 15 or <= -25
        else:
            color = mcolors.rgb2hex(cmap(row['normalized_snr']))

        popup_info = (
            f"{os.path.basename(csv_file)}<br>"
            f"SNR: {row['rx snr']}<br>"
            f"Elevation: {row['rx elevation']}<br>"
            f"Latitude: {row['rx lat']}<br>"
            f"Longitude: {row['rx long']}"
        )
        folium.CircleMarker(
            location=[row['rx lat'], row['rx long']],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_info, max_width=None)
        ).add_to(layer)

    return layer

def create_map_with_layers(csv_files, output_file):
    # Base map
    initial_df = pd.read_csv(csv_files[0])
    initial_map_center = [initial_df['rx lat'].mean(), initial_df['rx long'].mean()]
    m = folium.Map(location=initial_map_center, zoom_start=13, tiles="OpenStreetMap", control_scale=True)

    # Create a merged CSV file to use for calculating heatmaps etc
    df_list = []
    for file in csv_files:
        df = pd.read_csv(file)
        df_list.append(df)
    merged_df = pd.concat(df_list, ignore_index=True)

    # Prepare data for a heatmap
    heat_data = [[row['rx lat'], row['rx long'], row['rx snr']] for index, row in merged_df.iterrows()]

    # Add the heatmap layer
    heatmap_layer = folium.FeatureGroup(name='Measurement Heatmap', show=False)
    HeatMap(heat_data).add_to(heatmap_layer)
    heatmap_layer.add_to(m)

    # Measure Tool
    m.add_child(MeasureControl(
        active_color='blue',
        completed_color='blue',
        primary_length_unit='miles',
        secondary_length_unit='meters',
        tertiary_length_unit='feet',
        primary_area_unit=None,
        secondary_area_unit=None,
        tertiary_area_unit=None
    ))

    # Add full Screen option to zoom control
    fullscreen = Fullscreen()
    m.add_child(fullscreen)

    # Show long/lat mouse coordinates in lower right corner
    mouse_position = MousePosition(
        position="bottomright",
        separator=" | "
    )
    m.add_child(mouse_position)

    # Map layers
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        name="Esri WorldImagery"
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr='Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors,'
             '<a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> '
             '(<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
        name="OpenTopoMap"
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr="Map tiles by CartoDB, under CC BY 3.0. Data by OpenStreetMap, under ODbL.",
        name="CartoDB Positron"
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/light_nolabels/{z}/{x}/{y}{r}.png",
        attr="Map tiles by CartoDB, under CC BY 3.0. Data by OpenStreetMap, under ODbL.",
        name="CartoDB Positron (No Labels)"
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/dark_nolabels/{z}/{x}/{y}{r}.png",
        attr="Map tiles by CartoDB, under CC BY 3.0. Data by OpenStreetMap, under ODbL.",
        name="CartoDB Dark Matter (No Labels)"
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr="Map tiles by CartoDB, under CC BY 3.0. Data by OpenStreetMap, under ODbL.",
        name="CartoDB Dark Matter"
    ).add_to(m)

    # CSV layers
    for csv_file in csv_files:
        layer = create_point_layer(csv_file)
        if layer:
            layer.add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)
    m.save(output_file)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_files = glob.glob(os.path.join(script_dir, "*.csv"))

    if not csv_files:
        print("No CSV files found in the directory. Exiting.")
        exit(1)

    output_file = 'rangetest-map.html'
    create_map_with_layers(csv_files, output_file)
    print(f"Map with layers has been generated and can be viewed in '{output_file}'.")
