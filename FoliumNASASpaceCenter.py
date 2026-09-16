#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 11 10:43:15 2024

@author: kathrynhopkins
"""
'''
This code produces a Folium map of the location of the NASA Johnson Space Center in South-East Houston, Texas, USA
'''
#%% Import packages
import folium
from folium.features import DivIcon
#%% Create Folium map
# Set the location of the space center
nasa_coordinate = [29.559684888503615, -95.0830971930759]
# Set the location of the label marker
nasa_coordinate2 = [29.55, -95.05]
# Initialise the map
site_map = folium.Map(location = nasa_coordinate, zoom_start =10)
#Create a black cirlce at NASA and a pop-up label (for the HTML version)
circle = folium.Circle(nasa_coordinate, radius = 1000, color = 'black', fill = True).add_child(folium.Popup('NASA Johnson Space Center'))
# Add the label marker
marker = folium.map.Marker(
    nasa_coordinate2,
    icon = DivIcon(
        icon_size = (20,20),
        icon_anchor = (0,0),
        html = '<div style="font-size: 25;color:black;"><b>%s</b></div>' % 'NASA Johnson Space Center',
        )
    )
site_map.add_child(circle)
site_map.add_child(marker)
# Add a title to the map
map_title = "NASA Johnson Space Center Location"
title_html = f'<h1 style="position:absolute;z-index:100000;left:40vw" >{map_title}</h1>'
site_map.get_root().html.add_child(folium.Element(title_html))
# Save the map as HTML
site_map.save('NASA_JSC.html')
#%% Convert HTML map to png
import io
from PIL import Image
site_map_data = site_map._to_png(5)
img = Image.open(io.BytesIO(site_map_data))
img.save('NASA_JSC.png')
#%% Done!