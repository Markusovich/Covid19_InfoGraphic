# imports
import pandas as pd
from sodapy import Socrata
from flask import Flask, render_template, request, redirect
from IPython.display import HTML
import numpy as np
import json
from geojson import load
import plotly.express as px
import folium

app = Flask(__name__)



# generates a choropleth map based on the input data, defaults to total number of deaths
def genMap(data= results_df, data_to_display ='deaths'):
    # opens a geojson file containing county outlines
    with open('us_states') as file:
        states = load(file)

    map_data = pd.DataFrame()
    map_data["stateFIPS"] = data["stateFIPS"].astype(str)
    map_data["state_name"] = data["state_name"]

    # pads 'stateFIPS' to the correct length for states with single digit FIPS codes
    for i, row in map_data.iterrows():
        if len(map_data["stateFIPS"].iloc[i]) < 5:
            map_data["stateFIPS"].iloc[i] = "0" + map_data["stateFIPS"].iloc[i]

    if data_to_display == 'deaths':
        map_data["Deaths"] = data[data.columns[len(data.columns) - 1]].astype(int)
        scale = (0, 100)
        color_label = "Deaths"
        color_scale = "reds"

    elif data_to_display == 'cases':
        map_data["Cases"] = data[data.columns[len(data.columns) - 1]].astype(int)
        scale = (0, 1500)
        color_label = "Cases"
        color_scale = "blues"

    # escape for unsupported input
    else:
        return

    # generates a county level choropleth map of the United States
    fig = plotly.express.choropleth(map_data, home=states, locations='stateFIPS', color=color_label,
                                    color_continuous_scale=color_scale, featureidkey='properties.GEOID',
                                    scope="usa", range_color=scale,  hover_data=["state_name"])

    # adjusts the map's margins and disables the ability to drag it
    fig.update_layout(height=300, margin={"r": 15, "t": 15, "l": 15, "b": 15})
    fig.show()

    return render_template('datavisualization.html')






if __name__ == "__main__":
    app.run(debug = True)