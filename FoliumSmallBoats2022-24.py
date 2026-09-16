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
import webbrowser
import folium
import pandas as pd
import xyzservices.providers as xyz
import json
import geojson
from urllib.request import urlopen
#%% =============================================================================
# Prepare data for plotting
# =============================================================================
#The published migration statistcs are available here: https://www.gov.uk/government/statistics/statistics-relating-to-the-illegal-migration-bill
# This code pulls in the workbook named 'statistics-relating-to-the-illegal-migration-act-data-tables-to-apr2024.ods', and the second worksheet named 'IMB_01B' which lists the volumes of small boat arrivals by month from Jan 22 to Apr 24, by country of origin. In this script, the workbook has been downloaded and read into Pandas rather than being scraped directly via the URL
# Read in the downloaded data
a = pd.read_excel("statistics-relating-to-the-illegal-migration-act-data-tables-to-apr-2024.ods",'IMB_01b', engine="odf", header = 1, skiprows = 1)
# Delete the unwanted column at the end of the table
del a['End of table']
# Calculate a 'Total' column for each nationality
a['Total']=a.sum(axis = 1)
# Drop the summary rows at the bottom the table
small_boats = a[:19]
# Select the columns of interest
small_boats = small_boats[['Nationality', 'Total']]
#Rename the columns
small_boats.columns = ['Country', 'Total']
# Check how many rows (countries) in the dataset
len(small_boats)
# The latitude and longitude of each country of interest are needed. There are a number of lists available on the internet, and two have been used in this script. The first provides an average lat and long for each country, that is, it provides the coordinates for the centre of each country. It's available here: https://gist.github.com/tadast/8827699. Again, the CSV was downloaded rather than the data being scraped directly from the URL.
#Read in the downloaded CSV
country_coord = pd.read_csv('country-coord.csv')
# Change the country names that don't match as a merge will be conducted on country name with the small boats data
country_coord.replace(to_replace = ['Iran, Islamic Republic of', 'Viet Nam', 'Syrian Arab Republic'], value = ['Iran', 'Vietnam', 'Syria'], inplace = True)
# Merge the small boats data with the country-coord data to get the latitude and longitude of the centre of each country
small_boats_merge = pd.merge(small_boats, country_coord, on='Country', how = 'left')
# Check the columns and a few individual values
small_boats_merge.columns
small_boats_merge['Country'][17]
#%% Source the polygon shapes for each country (not the centre of each country, but its actual shape and location). This time, the data were scraped as below
url = 'https://raw.githubusercontent.com/python-visualization/folium/master/examples/data'
# Set the URL
country_shapes = f'{url}/world-countries.json'
# Open the URL
response = urlopen(country_shapes)
# Read in the json file
data_json = json.loads(response.read())
# Check the contents
data_json['features'][0]['properties']['name']
# Normalise the json file so it's easier to read
df = pd.json_normalize(data_json['features'])
#%% Here's another file with country shapes. This one has been scraped, and the json has been normalised into a DataFrame so that the contents are easy to view. The data from this file is not used in the chart, it's simply for information. Sometimes one source may be more suitable or reliable than another, and in some cases you might want to use both files (e.g. depending on how the countries have been named and listed).
# Set the URL
# political_countries_url = ("https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json")
# # Send a request
# response = urlopen(political_countries_url)
# # Read the data
# data_json = json.loads(response.read())
# # Check some of the values
# data_json['features'][139]['properties']['name']
# # Turn the entire json into a dataframe
# df = pd.json_normalize(data_json['features'])
#%% And now plot
# First, initialise a folium map based on the centre(!) of the world
SmallBoats = folium.Map(location = (30,10), zoom_start = 3, tiles = 'Esri.WorldShadedRelief')
# Now add the Choropleth
folium.Choropleth(
    geo_data = country_shapes,# Here are the coordinates of each country's polygon
    data = small_boats_merge, # Here are the countries we want to plot and their values (the numbers of migrants arriving by small boats
    columns = ['Country', 'Total'],# These are the columns we want to use
    key_on = 'feature.properties.name',# Here's our match to the geojson file
    fill_color = 'YlOrRd',
    fill_opacity = 0.8,
    line_opacity = 0.1,
    nan_fill_color = 'lightgrey',
    legend_name = 'UK Arrival Volumes January 2022 to April 2024',size = 20,
    ).add_to(SmallBoats)
# Add a bsepoke marker for Albania only so that it's not obscured by either the country fill colour or the circle marker we're adding later
#Albania
folium.Marker(location = [small_boats_merge['Latitude (average)'][1]+5, small_boats_merge['Longitude (average)'][1]],
    popup = small_boats_merge['Country'][1],
    icon = folium.DivIcon(html=f"""<div style= "font-family:courier new; 
                          color:black;
                          font-size: 10px;
                          background-color:None
                          border:None
                          padding:None
                          margin:None">{small_boats_merge['Country'][1]}</div>""")).add_to(SmallBoats)
SmallBoats.save('SmallBoats.html')
#%% Now label all of the other countries at once (excluding Albania):
#for i in range(0, len(small_boats_merge)):
for i in [0,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18]:
        folium.Marker(
            location = [small_boats_merge.iloc[i]['Latitude (average)'],
                        small_boats_merge.iloc[i]['Longitude (average)']],
            popup = small_boats_merge.iloc[i]['Country'],
            icon = folium.DivIcon(html=f"""<div style= "font-family:courier new;
                                  color:black;
                                  ">{small_boats_merge.iloc[i]['Country']}</div>""")).add_to(SmallBoats)
SmallBoats.save('SmallBoats.html')
#%% Now label the UK and the chart
#UK Label
folium.Marker(location = [55, 0],
    popup = df['properties.name'][57],
    icon = folium.DivIcon(html=f"""<div style= "font-family:courier new; 
                          color:black;
                          font-size: 15px;
                          background-color:None
                          border:None
                          padding:None
                          margin:None">{df['properties.name'][57]}</div>""")).add_to(SmallBoats)
#Title Marker
folium.Marker(location = [54,-20],
              icon = folium.DivIcon(
                  html="""
                  <span>Small Boat Arrivals UK 2022-2024</span>
                  """, class_name = "mapText")).add_to(SmallBoats)
SmallBoats.get_root().html.add_child(folium.Element("""
                                                    <style>
                                                    .mapText {
                                                        color:black;
                                                        font-family:courier new;
                                                        font-weight:bold;
                                                        font-size:20px}
                                                    </style>"""))
SmallBoats.save('SmallBoats.html')
# Add a Circle Marker to Albania to highlight it
radius = 25
folium.CircleMarker(
    location=[41, 20],
    radius=radius,
    color="black",
    stroke=True,
    fill=False,
    fill_opacity=0.6,
    opacity=1,
    popup="{} pixels".format(radius),
    tooltip=False,
).add_to(SmallBoats)
SmallBoats.save('SmallBoats.html')
# Add map marker to the destination country, the UK
folium.Marker([55, -3]).add_to(SmallBoats)
# folium.RegularPolygonMarker(location=(46, 6), color = 'black', fill_color = 'black', number_of_sides=3, radius=20, rotation=90).add_to(SmallBoats)
SmallBoats.save('SmallBoats.html')
#%% Convert to png to create an image rather than a web-page
import io
from PIL import Image
SmallBoats_data = SmallBoats._to_png(5)
img = Image.open(io.BytesIO(SmallBoats_data))
img.save('SmallBoats.png')
#%% Done!