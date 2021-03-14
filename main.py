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
import folium
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

    return known_cases_df

def getCountyDeathData():
    url2 = "https://static.usafacts.org/public/data/covid-19/covid_deaths_usafacts.csv?_ga=2.8737845.1498587340.1614544717-1622888718.1614364715"
    s2 = requests.get(url2).content
    deaths_df = pd.read_csv(io.StringIO(s2.decode('utf-8')))
    deaths_df = deaths_df.drop(
        ['countyFIPS', 'StateFIPS'], 1)
    deaths_df = deaths_df[deaths_df["County Name"] != "Statewide Unallocated"]
    deaths_df = deaths_df.dropna().reset_index(drop=True)

    return deaths_df

# Homepage. This is what the user sees when they click on the link to our website.
# The home.html file is rendered when the website route is at /
@app.route('/')
def homefunc():
    return render_template('home.html')

@app.route('/datasearchcounty', methods=['GET', 'POST'])
def datafunc2():
    
    if request.method == 'POST':
        state = request.form['state_name']
        caseData = getCountyCaseData()
        deathData = getCountyDeathData()

        caseData = caseData[caseData['State'] == state].reset_index(drop=True)
        deathData = deathData[deathData['State'] == state].reset_index(drop=True)

        county = request.form['county']
        county = county + " "
        caseData = caseData[caseData['County Name'] == county].reset_index(drop=True)
        deathData = deathData[deathData['County Name'] == county].reset_index(drop=True)

        caseData = caseData.drop(['State', 'County Name'], axis=1)
        deathData = deathData.drop(['State', 'County Name'], axis=1)

        # Getting date range input
        daterange = request.form['daterange']
        daterange = daterange.split(" to ")
        startDate = daterange[0]
        endDate = daterange[1]


        # Getting rid of all dates that fall outside of our range in the dataset
        for key in caseData.keys():
            if key < startDate or key >= endDate:
                caseData = caseData.drop([key], axis=1)

        for key in deathData.keys():
            if key < startDate or key >= endDate:
                deathData = deathData.drop([key], axis=1)

        caseData = caseData[caseData.columns[::-1]]
        deathData = deathData[deathData.columns[::-1]]

        numarr = [None] * 10000
        i = 0
        for key in caseData:
            numarr[i] = caseData.at[0, key]
            i = i+1

        numarr2 = [None] * 10000
        i2 = 0
        for key in deathData:
            numarr2[i2] = deathData.at[0, key]
            i2 = i2+1

        nc = {}
        nd = {}
        j = 0
        for key in caseData:
            if numarr[j+1] == None:
                break
            nc[key] = numarr[j] - numarr[j+1]
            j = j + 1
        newCaseData = pd.DataFrame(list(nc.items()), columns=['Date', 'Value'])

        j = 0
        for key in deathData:
            if numarr2[j+1] == None:
                break
            nd[key] = numarr2[j] - numarr2[j+1]
            j = j + 1
        newDeathData = pd.DataFrame(list(nd.items()), columns=['Date', 'Value'])


        # Here we create python graphs and save them to png files so that they can be displayed on html
        plt.figure(figsize=(12, 4))
        plt.xticks(rotation=45)
        plt.style.use('dark_background')
        plt.tight_layout()
        plt.plot(newCaseData['Date'], newCaseData['Value'])
        plt.savefig('./static/nothing2.png')

        caseData = caseData[caseData.columns[::-1]]
        fig, ax = plt.subplots(figsize=(12, 4))
        plt.xticks(rotation=25)
        plt.style.use('dark_background')
        ax.plot(pd.to_datetime(caseData.keys()), caseData.iloc[0])
        plt.tight_layout()
        if len(caseData.columns) > 14 and len(caseData.columns) < 90:
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            plt.savefig('./static/totalCountyCases.png')
        if len(caseData.columns) >= 90:
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            ax.xaxis.set_major_formatter(DateFormatter("%m/%Y"))
            plt.savefig('./static/totalCountyCases.png')  
        else:
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            plt.savefig('./static/totalCountyCases.png')

        newCaseData = newCaseData[newCaseData.columns[::-1]]
        fig, ax = plt.subplots(figsize=(12, 4))
        plt.xticks(rotation=25)
        plt.style.use('dark_background')
        ax.plot(pd.to_datetime(newCaseData.reset_index(
            drop=True)['Date']), newCaseData['Value'], '-o')
        plt.tight_layout()
        if len(newCaseData) > 14 and len(newCaseData) < 90:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/newCountyCases.png')
        if len(newCaseData) >= 90:
            ax.xaxis.set_major_formatter(DateFormatter("%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/newCountyCases.png')  
        else:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/newCountyCases.png')

        deathData = deathData[deathData.columns[::-1]]
        fig, ax = plt.subplots(figsize=(12, 4))
        plt.xticks(rotation=25)
        plt.style.use('dark_background')
        ax.plot(pd.to_datetime(deathData.keys()), deathData.iloc[0])
        plt.ylim(ymin=0)
        plt.tight_layout()
        if len(deathData.columns) > 14 and len(deathData.columns) < 90:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/totalCountyDeaths.png')
        if len(deathData.columns) >= 90:
            ax.xaxis.set_major_formatter(DateFormatter("%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/totalCountyDeaths.png')  
        else:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/totalCountyDeaths.png')

        newDeathData = newDeathData[newDeathData.columns[::-1]]
        fig, ax = plt.subplots(figsize=(12, 4))
        plt.xticks(rotation=25)
        plt.style.use('dark_background')
        ax.plot(pd.to_datetime(newDeathData.reset_index(
            drop=True)['Date']), newDeathData['Value'], '-o')
        plt.ylim(ymin=0)
        plt.tight_layout()
        if len(newDeathData) > 14 and len(newDeathData) < 90:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/newCountyDeaths.png')
        if len(newDeathData) >= 90:
            ax.xaxis.set_major_formatter(DateFormatter("%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/newCountyDeaths.png')  
        else:
            ax.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            ax.xaxis.set_minor_locator(plt.MultipleLocator(1))
            plt.savefig('./static/newCountyDeaths.png')


        post = "This is a post"
        return render_template('datasearchcounty.html', post=post)
        '''
        return render_template('datasearchcounty.html')
        '''
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

@app.route('/datavisualizationstate', methods=['GET', 'POST'])
def base():
    if request.method == 'POST':

        searchby = request.form['searchBy']
        data = getStateData()

        # Getting date range input
        daterange = request.form['daterange']
        startDate = daterange.split(" to ")[0]
        endDate = daterange.split(" to ")[1]
        # Getting rid of all dates that fall outside of our range in the dataset
        data = data[data.submission_date >= startDate]
        data = data[data.submission_date <= endDate]

        # Replacing all null values as 0
        data = data.fillna(0)
        # Changing columns to difference datatype so we can manipulate the numbers
        data[["tot_cases", "new_case", "tot_death", "new_death"]] = data[[
            "tot_cases", "new_case", "tot_death", "new_death"]].astype('float')
        data[["tot_cases", "new_case", "tot_death", "new_death"]] = data[[
            "tot_cases", "new_case", "tot_death", "new_death"]].astype('int')

        data.reset_index(drop=True, inplace=True)

        statePopulations = {'state': ["AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA", 
          "HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", 
          "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH", 
          "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI", "SC", 
          "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY"], 
          'population': [724357,4934190,3033950,7520100,39613500,5893630,3552820,714153,990334,21944600,10830000,
          1406430,3167970,1860120,12569300,6805660,2917220,4480710,4627000,6912240,6065440,
          1354520,9992430,5706400,6169040,2966410,1085000,10701000,770026,1952000,1372200,
          8874520,2105000,3185790,19300000,11714600,3990440,4289440,12804100,1061510,5277830,
          896581,6944260,29730300,3310770,8603980,623251,7796940,5852490,1767860,581075]}

        data = data.rename(columns={"tot_cases": "Total Cases", "new_case": "New Cases", "tot_death": "Total Deaths", "new_death": "New Deaths"})

        states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", 
          "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
          "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
          "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
          "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]
        data = data[data['state'].isin(states)]

        if searchby == 'New Cases' or searchby == 'New Deaths':
            data = data.groupby(['state'], as_index=False).sum([searchby])
            data = data[["state", searchby]]
        else:
            if searchby == 'Cases per 100,000':
                data = data.groupby(['state'], as_index=False).sum(['Total Cases'])
                data = data.rename(columns={"Total Cases": "Cases per 100,000"})
                data = data[["state", 'Cases per 100,000']]
                data['Cases per 100,000'] = (data['Cases per 100,000'] / statePopulations['population']) * 100000
                searchby = 'Cases per 100,000'
            else:
                data = data.groupby(['state'], as_index=False).sum(['Total Deaths'])
                data = data.rename(columns={"Total Deaths": "Deaths per 100,000"})
                data = data[["state", 'Deaths per 100,000']]
                data['Deaths per 100,000'] = (data['Deaths per 100,000'] / statePopulations['population']) * 100000
                searchby = 'Deaths per 100,000'

        url = (
            "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data"
        )
        state_geo = f"{url}/us-states.json"

        m = folium.Map(width=1000, height=600, location=[39.8283, -98.5795], zoom_start=4)

        folium.Choropleth(
            geo_data=state_geo,
            name="choropleth",
            data=data,
            columns=["state", searchby],
            key_on="feature.id",
            fill_color="YlOrRd",
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=searchby,
        ).add_to(m)

        style_function = lambda x: {'fillColor': '#ffffff', 
                                    'color':'#000000', 
                                    'fillOpacity': 0.1, 
                                    'weight': 0.1}
        highlight_function = lambda x: {'fillColor': '#000000', 
                                        'color':'#000000', 
                                        'fillOpacity': 0.50, 
                                        'weight': 0.1}


        NIL = folium.features.GeoJson(
            state_geo,
            style_function=style_function,
            control=False,
            highlight_function=highlight_function,
            tooltip=folium.features.GeoJsonTooltip(
                fields=["name"],
                aliases=[''],
                style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;") 
            )
        ).add_to(m)

        m.add_child(NIL)
        m.keep_in_front(NIL)


        folium.LayerControl().add_to(m)
        m.save("templates/map.html")
        return render_template('displaymap.html', searchby=searchby, daterange=daterange)
    else:
        return render_template('datavisualizationstate.html')