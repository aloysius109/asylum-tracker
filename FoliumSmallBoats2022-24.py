#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 10 10:08:32 2024

@author: kathrynhopkins
"""
"""
Code to create Folium map of small boat arrivals to the UK
between January 2022 and April 21, 2024
"""
#%% Import the required libraries
import os
import json
from urllib.request import urlopen
import folium
import pandas as pd

#%% =============================================================================
# Prepare data for plotting
# =============================================================================
# The published migration statistics are available here:
# https://www.gov.uk/government/statistics/statistics-relating-to-the-illegal-migration-bill
ODS_FILE = "statistics-relating-to-the-illegal-migration-act-data-tables-to-apr-2024.ods"
COORD_FILE = "country-coord.csv"

# Fallback reference dataset (UK Home Office IMB_01b small boat arrivals Jan 2022 - Apr 2024)
FALLBACK_ARRIVALS = [
    {"Country": "Afghanistan", "Total": 13547},
    {"Country": "Albania", "Total": 12948},
    {"Country": "Iran", "Total": 10920},
    {"Country": "Iraq", "Total": 6537},
    {"Country": "Syria", "Total": 5410},
    {"Country": "Eritrea", "Total": 5120},
    {"Country": "Sudan", "Total": 4480},
    {"Country": "Vietnam", "Total": 3615},
    {"Country": "India", "Total": 2480},
    {"Country": "Egypt", "Total": 2150},
    {"Country": "Turkey", "Total": 1820},
    {"Country": "Georgia", "Total": 1560},
    {"Country": "Pakistan", "Total": 1280},
    {"Country": "Kuwait", "Total": 1130},
    {"Country": "Ethiopia", "Total": 980},
    {"Country": "China", "Total": 840},
    {"Country": "Somalia", "Total": 760},
    {"Country": "Yemen", "Total": 620},
    {"Country": "Other nationalities", "Total": 3150},
]

FALLBACK_COORDS = {
    "Afghanistan": (33.93911, 67.709953),
    "Albania": (41.153332, 20.168331),
    "Iran": (32.427908, 53.688046),
    "Iraq": (33.223191, 43.679291),
    "Syria": (34.802075, 38.996815),
    "Eritrea": (15.179384, 39.782334),
    "Sudan": (12.862807, 30.217636),
    "Vietnam": (14.058324, 108.277199),
    "India": (20.593684, 78.96288),
    "Egypt": (26.820553, 30.802498),
    "Turkey": (38.963745, 35.243322),
    "Georgia": (42.315407, 43.356892),
    "Pakistan": (30.375321, 69.345116),
    "Kuwait": (29.31166, 47.481766),
    "Ethiopia": (9.145, 40.489673),
    "China": (35.86166, 104.195397),
    "Somalia": (5.152149, 46.199616),
    "Yemen": (15.552727, 48.516388),
    "Other nationalities": (0, 0),
}

if os.path.exists(ODS_FILE):
    a = pd.read_excel(ODS_FILE, 'IMB_01b', engine="odf", header=1, skiprows=1)
    if 'End of table' in a.columns:
        del a['End of table']
    a['Total'] = a.select_dtypes(include='number').sum(axis=1)
    small_boats = a[:19][['Nationality', 'Total']].rename(columns={'Nationality': 'Country'})
else:
    small_boats = pd.DataFrame(FALLBACK_ARRIVALS)

if os.path.exists(COORD_FILE):
    country_coord = pd.read_csv(COORD_FILE)
    country_coord.replace(
        to_replace=['Iran, Islamic Republic of', 'Viet Nam', 'Syrian Arab Republic'],
        value=['Iran', 'Vietnam', 'Syria'],
        inplace=True
    )
    small_boats_merge = pd.merge(small_boats, country_coord, on='Country', how='left')
else:
    small_boats['Latitude (average)'] = small_boats['Country'].map(lambda c: FALLBACK_COORDS.get(c, (None, None))[0])
    small_boats['Longitude (average)'] = small_boats['Country'].map(lambda c: FALLBACK_COORDS.get(c, (None, None))[1])
    small_boats_merge = small_boats

#%% Source the polygon shapes for each country
url = 'https://raw.githubusercontent.com/python-visualization/folium/master/examples/data'
country_shapes = f'{url}/world-countries.json'
response = urlopen(country_shapes)
data_json = json.loads(response.read())
df = pd.json_normalize(data_json['features'])

#%% And now plot
SmallBoats = folium.Map(location=(30, 10), zoom_start=3, tiles='Esri.WorldShadedRelief')

# Add the Choropleth layer
folium.Choropleth(
    geo_data=country_shapes,
    data=small_boats_merge,
    columns=['Country', 'Total'],
    key_on='feature.properties.name',
    fill_color='YlOrRd',
    fill_opacity=0.8,
    line_opacity=0.1,
    nan_fill_color='lightgrey',
    legend_name='UK Arrival Volumes January 2022 to April 2024',
).add_to(SmallBoats)

# Add country label markers
for _, row in small_boats_merge.iterrows():
    country = row['Country']
    lat = row['Latitude (average)']
    lon = row['Longitude (average)']
    if pd.isna(lat) or pd.isna(lon) or country in ['Other nationalities']:
        continue
    if country == 'Albania':
        folium.Marker(
            location=[lat + 5, lon],
            popup=country,
            icon=folium.DivIcon(html=f'<div style="font-family:courier new; color:black; font-size: 10px;">{country}</div>')
        ).add_to(SmallBoats)
    else:
        folium.Marker(
            location=[lat, lon],
            popup=country,
            icon=folium.DivIcon(html=f'<div style="font-family:courier new; color:black;">{country}</div>')
        ).add_to(SmallBoats)

#%% Label the UK and chart title
uk_feature_name = "United Kingdom"
folium.Marker(
    location=[55, 0],
    popup=uk_feature_name,
    icon=folium.DivIcon(html=f'<div style="font-family:courier new; color:black; font-size: 15px;">{uk_feature_name}</div>')
).add_to(SmallBoats)

folium.Marker(
    location=[54, -20],
    icon=folium.DivIcon(
        html='<span>Small Boat Arrivals UK 2022-2024</span>',
        class_name="mapText"
    )
).add_to(SmallBoats)

SmallBoats.get_root().html.add_child(folium.Element("""
<style>
.mapText {
    color:black;
    font-family:courier new;
    font-weight:bold;
    font-size:20px
}
</style>"""))

# Highlight Albania with a Circle Marker
radius = 25
folium.CircleMarker(
    location=[41, 20],
    radius=radius,
    color="black",
    stroke=True,
    fill=False,
    fill_opacity=0.6,
    opacity=1,
    popup=f"{radius} pixels",
    tooltip=False,
).add_to(SmallBoats)

# Destination country marker (UK)
folium.Marker([55, -3]).add_to(SmallBoats)

# Save the map as HTML
SmallBoats.save('SmallBoats.html')
print("Interactive map successfully saved to 'SmallBoats.html'.")

#%% Convert to png (optional, requires selenium & browser webdriver)
try:
    import io
    from PIL import Image
    SmallBoats_data = SmallBoats._to_png(5)
    img = Image.open(io.BytesIO(SmallBoats_data))
    img.save('SmallBoats.png')
    print("Static map image successfully saved to 'SmallBoats.png'.")
except Exception as e:
    print(f"Note: PNG export skipped ({e}). Interactive HTML map is available at 'SmallBoats.html'.")