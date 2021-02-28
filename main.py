# All of the imports, ignore
import pandas as pd
from sodapy import Socrata
from flask import Flask, render_template, request, redirect
from IPython.display import HTML
from numpy import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
import json
from geojson import load
import plotly.express as px
import folium
import os.path
import io
import requests
import re
matplotlib.use('Agg')
app = Flask(__name__)

# This is so that the correct graphs get displayed, not older graphs
# Resets cache after every run
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

# This function returns a dataframe (dataset) of the most recent state covid data
# Everytime your run the project, a new dataset is always pulled from data.cdc.gov
def getStateData():
    # Importing data set to client variable
    client = Socrata("data.cdc.gov", None)
    results = client.get("9mfq-cb36", limit=100000)

    # Convert to pandas DataFrame so we can work with the dataset
    results_df = pd.DataFrame.from_records(results)

    # Removing unhelpful columns
    results_df = results_df.drop(
        ['consent_cases', 'consent_deaths', 'created_at', 'conf_cases', 'prob_cases', 'pnew_case', 'conf_death', 'prob_death', 'pnew_death'], 1)

    results_df['submission_date'] = pd.to_datetime(
        results_df['submission_date'])
    #results_df['submission_date'] = results_df['submission_date'].dt.strftime(
    #    '%Y-%m-%d')

    # Sorting dataframe so that most recent submissions are first
    results_df = results_df.sort_values(by='submission_date', ascending=False)

    # Our function returns the dataset containing all covid data that we will work with
    return results_df

def getCountyCaseData():
    url = "https://static.usafacts.org/public/data/covid-19/covid_confirmed_usafacts.csv?_ga=2.222696091.1498587340.1614544717-1622888718.1614364715"
    s = requests.get(url).content
    known_cases_df = pd.read_csv(io.StringIO(s.decode('utf-8')))
    known_cases_df = known_cases_df.drop(
        ['countyFIPS', 'StateFIPS'], 1)
    known_cases_df = known_cases_df[known_cases_df["County Name"] != "Statewide Unallocated"]
    known_cases_df = known_cases_df.dropna().reset_index(drop=True)

    for key in known_cases_df.keys():
        if re.match("[0-9]-[0-9]-[0-9]", key):
            known_cases_df[key] = pd.to_datetime(known_cases_df[key])

    return known_cases_df

def getCountyDeathData():
    url2 = "https://static.usafacts.org/public/data/covid-19/covid_deaths_usafacts.csv?_ga=2.8737845.1498587340.1614544717-1622888718.1614364715"
    s2 = requests.get(url2).content
    deaths_df = pd.read_csv(io.StringIO(s2.decode('utf-8')))
    deaths_df = deaths_df.drop(
        ['countyFIPS', 'StateFIPS'], 1)
    deaths_df = deaths_df[deaths_df["County Name"] != "Statewide Unallocated"]
    deaths_df = deaths_df.dropna().reset_index(drop=True)

    for key in deaths_df.keys():
        if re.match("[0-9]-[0-9]-[0-9]", key):
            deaths_df[key] = pd.to_datetime(deaths_df[key])

    return deaths_df


# Here we get the data by county
def getCountyData():

    client = Socrata("data.cdc.gov", None)
    results = client.get("kn79-hsxy", limit=5000)
    results_df = pd.DataFrame.from_records(results)
    results_df = results_df.drop(
        ['start_week', 'end_week', 'county_fips_code', 'urban_rural_code', 'total_death', 'footnote'], 1)
    results_df = results_df.dropna().reset_index(drop=True)

    if os.path.isfile('countyFile'):
        with open('countyFile', 'a') as f:
            if results_df['data_as_of'][0] > pd.read_csv("countyFile")['data_as_of'][0]:
                results_df.to_csv(f, header=False, index=False)
    else:
        with open('countyFile', 'a') as f:
            results_df.to_csv(f, header=True, index=False)

    results_df = pd.read_csv("countyFile")
    results_df['data_as_of'] = pd.to_datetime(
                results_df['data_as_of'])
    
    return results_df


# Homepage. This is what the user sees when they click on the link to our website.
# The home.html file is rendered when the website route is at /
@app.route('/')
def homefunc():
    return render_template('home.html')


@app.route('/datasearchcounty', methods=['GET', 'POST'])
def datafunc2():
    
    if request.method == 'POST':
        state = request.form['state_name']
        data = getCountyData()
        data = data[data['state_name'] == state].reset_index(drop=True)

        county = request.form['county']
        data = data[data['county_name'] == county].reset_index(drop=True)

        # Getting date range input
        daterange = request.form['daterange']
        daterange = daterange.split(" to ")
        startDate = daterange[0]
        endDate = daterange[1]
        # Getting rid of all dates that fall outside of our range in the dataset
        data = data[data.data_as_of >= startDate]
        data = data[data.data_as_of < endDate]

        data[["covid_death"]] = data[["covid_death"]].astype('float')
        data[["covid_death"]] = data[["covid_death"]].astype('int')
        data.reset_index(drop=True, inplace=True)

        data = data.rename(columns={"data_as_of": "Date", "state_name": "State", "county_name": "County",
                                    "covid_death": "Total Covid Deaths"})

        # Here we create python graphs and save them to png files so that they can be displayed on html
        plt.figure(figsize=(12, 4))
        plt.xticks(rotation=45)
        plt.style.use('dark_background')
        plt.tight_layout()
        plt.plot(data.sort_values('Date', ascending=True).reset_index(
            drop=True)['Date'], data['Total Covid Deaths'][::-1].astype('int'))
        plt.savefig('./static/nothing2.png')

        fig, ax = plt.subplots(figsize=(12, 4))
        plt.xticks(rotation=25)
        plt.style.use('dark_background')
        ax.plot(data.sort_values('Date', ascending=True).reset_index(
            drop=True)['Date'], data['Total Covid Deaths'][::-1].astype('int'), '-o')
        plt.tight_layout()
        if len(data) > 14 and len(data) < 90:
            print("Shit")
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/totalDeaths_county.png')
        if len(data) >= 90:
            ax.xaxis.set_major_formatter(DateFormatter("%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/totalDeaths_county.png')
        else:
            print("Nice")
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/totalDeaths_county.png')


        post = "This is a post"
        return render_template('datasearchcounty.html', dataColumns=data.keys(), dataItems=data.to_numpy(), post=post)
    else:
        return render_template('datasearchcounty.html')


# This is the code that is executed when the website route is /datasearchstate
@app.route('/datasearchstate', methods=['GET', 'POST'])
def datafunc():

    # If you submit the form in datasearchstate.html, then this code is executed
    if request.method == 'POST':

        # Getting the input from the state field in the form in datasearchstate.html
        # Based on the state, we eliminate all other states from the dataset we get from data.cdc.gov
        # This was we are narrowing our dataset
        state = request.form['state']
        if state != "None":
            data = getStateData()
            data = data[data['state'] == state]
        else:
            data = getStateData()
            pass

        # Getting date range input
        daterange = request.form['daterange']
        daterange = daterange.split(" to ")
        startDate = daterange[0]
        endDate = daterange[1]
        # Getting rid of all dates that fall outside of our range in the dataset
        data = data[data.submission_date >= startDate]
        data = data[data.submission_date < endDate]

        # Replacing all null values as 0
        data = data.fillna(0)
        # Changing columns to difference datatype so we can manipulate the numbers
        data[["tot_cases", "new_case", "tot_death", "new_death"]] = data[[
            "tot_cases", "new_case", "tot_death", "new_death"]].astype('float')
        data[["tot_cases", "new_case", "tot_death", "new_death"]] = data[[
            "tot_cases", "new_case", "tot_death", "new_death"]].astype('int')

        data.reset_index(drop=True, inplace=True)

        # Get the shuffle input, and order the dataset based on the shuffle input from the form
        shuffle = request.form['shuffle']
        if shuffle != "None":
            for i in data.keys():
                if shuffle == str(i):
                    data = data.sort_values(by=[shuffle], ascending=False)
                    break
        else:
            pass

        # Here we rename the columns so that they make more sense
        # For example 'Total Deaths' is easier to understand than 'tot_death'
        data = data.rename(columns={"submission_date": "Date", "state": "State", "tot_cases": "Total Cases",
                                    "new_case": "New Cases",
                                    "tot_death": "Total Deaths",
                                    "new_death": "New Deaths", })

        
        # Here we create python graphs and save them to png files so that they can be displayed on html
        plt.figure(figsize=(12, 4))
        plt.xticks(rotation=45)
        plt.style.use('dark_background')
        plt.tight_layout()
        plt.plot(data.sort_values('Date', ascending=True).reset_index(
            drop=True)['Date'], data['Total Cases'][::-1].astype('int'))
        plt.savefig('./static/nothing.png')

        fig, ax = plt.subplots(figsize=(12, 4))
        plt.xticks(rotation=25)
        plt.style.use('dark_background')
        ax.plot(data.sort_values('Date', ascending=True).reset_index(
            drop=True)['Date'], data['Total Cases'][::-1].astype('int'))
        plt.tight_layout()
        if len(data) > 14 and len(data) < 90:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/totalCases.png')
        if len(data) >= 90:
            ax.xaxis.set_major_formatter(DateFormatter("%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/totalCases.png')  
        else:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            plt.savefig('./static/totalCases.png')

        fig, ax = plt.subplots(figsize=(12, 4))
        plt.xticks(rotation=25)
        plt.style.use('dark_background')
        ax.plot(data.sort_values('Date', ascending=True).reset_index(
            drop=True)['Date'], data['Total Deaths'][::-1].astype('int'))
        plt.tight_layout()
        if len(data) > 14 and len(data) < 90:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/totalDeaths.png')
        if len(data) >= 90:
            ax.xaxis.set_major_formatter(DateFormatter("%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/totalDeaths.png')  
        else:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            plt.savefig('./static/totalDeaths.png')

        fig, ax = plt.subplots(figsize=(12, 4))
        plt.xticks(rotation=25)
        plt.style.use('dark_background')
        ax.plot(data.sort_values('Date', ascending=True).reset_index(
            drop=True)['Date'], data['New Deaths'][::-1].astype('int'), '-o')
        plt.ylim(ymin=0)
        plt.tight_layout()
        if len(data) > 14 and len(data) < 90:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/newDeaths.png')
        if len(data) >= 90:
            ax.xaxis.set_major_formatter(DateFormatter("%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/newDeaths.png')  
        else:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            plt.savefig('./static/newDeaths.png')

        fig, ax = plt.subplots(figsize=(12, 4))
        plt.xticks(rotation=25)
        plt.style.use('dark_background')
        ax.plot(data.sort_values('Date', ascending=True).reset_index(
            drop=True)['Date'], data['New Cases'][::-1].astype('int'), '-o')
        plt.ylim(ymin=0)
        plt.tight_layout()
        if len(data) > 14 and len(data) < 90:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/newCases.png')
        if len(data) >= 90:
            ax.xaxis.set_major_formatter(DateFormatter("%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/newCases.png')  
        else:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            plt.savefig('./static/newCases.png')


        # Adding commas to big numbers
        
        data["Total Cases"] = data["Total Cases"].apply(lambda x: "{:,}".format(x))
        data["New Cases"] = data["New Cases"].apply(lambda x: "{:,}".format(x))
        data["Total Deaths"] = data["Total Deaths"].apply(lambda x: "{:,}".format(x))
        data["New Deaths"] = data["New Deaths"].apply(lambda x: "{:,}".format(x))

        # Here we pass our dataset that we filtered based on the input parameters from the search form
        # Because we passed the dataset, we are then able to print it to the html file
        # The html file 'datasearchstate.html' gets the dataset and now the html file can print it
        post = "This is a post"
        return render_template('datasearchstate.html', dataColumns=data.keys(), dataItems=data.to_numpy(), post=post)
    else:
        # If we load the page then this file shows up
        return render_template('datasearchstate.html')


# Tylers route, he is working on this page
@app.route('/datavisualization')
# generates a choropleth map based on the input data, defaults to total number of deaths
def genMap(data= getStateData(), data_to_display ='deaths'):
    # opens a geojson file containing county outlines
    with open('us_states.geojson') as file:
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
