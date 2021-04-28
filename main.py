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
import branca
import gunicorn
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

    # Sorting dataframe so that most recent submissions are first
    results_df = results_df.sort_values(by='submission_date', ascending=False)

    # Our function returns the dataset containing all covid data that we will work with
    return results_df

print(getStateData())

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

def getCountyFIPS():

    url = "https://static.usafacts.org/public/data/covid-19/covid_confirmed_usafacts.csv?_ga=2.222696091.1498587340.1614544717-1622888718.1614364715"
    s = requests.get(url).content
    known_cases_df = pd.read_csv(io.StringIO(s.decode('utf-8')))

    known_cases_df['countyFIPS'] = known_cases_df['countyFIPS'].apply(str)
    known_cases_df['countyFIPS'] = known_cases_df[known_cases_df['countyFIPS'] != "0"].reset_index(drop=True)

    return known_cases_df['countyFIPS']


# Homepage. This is what the user sees when they click on the link to our website.
# The home.html file is rendered when the website route is at /
@app.route('/')
def homefunc():
    return render_template('home.html')

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
        data = data[data.submission_date <= endDate]

        if data.empty:
            return render_template('datasearchstate.html', invalidmessage="Error. Invalid date range.")

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
        return render_template('datasearchstate.html', dataColumns=data.keys(), dataItems=data.to_numpy(), post=post, state=state, shuffle=shuffle)
    else:
        # If we load the page then this file shows up
        return render_template('datasearchstate.html')

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
            if key < startDate or key > endDate:
                caseData = caseData.drop([key], axis=1)

        for key in deathData.keys():
            if key < startDate or key > endDate:
                deathData = deathData.drop([key], axis=1)

        caseData = caseData[caseData.columns[::-1]]
        deathData = deathData[deathData.columns[::-1]]

        if caseData.empty or deathData.empty:
            return render_template('datasearchcounty.html', invalidmessage="Error. Invalid date range.")

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
        return render_template('datasearchcounty.html', post=post, state=state, county=county)
    else:
        return render_template('datasearchcounty.html')


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

        if data.empty:
            return render_template('datavisualizationstate.html', invalidmessage="Error. Invalid date range.")

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

        with open("us-states.json", "r") as configJSON:
            state_geo = json.load(configJSON)
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
                                    'weight': 0.05}
        highlight_function = lambda x: {'fillColor': '#000000', 
                                        'color':'#000000', 
                                        'fillOpacity': 0.50, 
                                        'weight': 0.05}

        for state in state_geo['features']:
            state['properties']['Value'] = str(data.loc[data['state'] == state['id'], searchby].item())

        NIL = folium.features.GeoJson(
            state_geo,
            style_function=style_function,
            control=False,
            highlight_function=highlight_function,
            tooltip=folium.features.GeoJsonTooltip(
                fields=["name", "Value"],
                aliases=['', ''],
                style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;") 
            )
        ).add_to(m)

        m.add_child(NIL)
        m.keep_in_front(NIL)

        folium.LayerControl().add_to(m)
        m.save("templates/map.html")
        return render_template('datavisualizationstate.html', searchby=searchby, daterange=daterange, states=json.dumps(data['state'].tolist()), values=json.dumps(data[searchby].tolist()), searchby2=json.dumps(searchby))
    else:
        return render_template('datavisualizationstate.html')

@app.route('/datavisualizationcounty', methods=['GET', 'POST'])
def base2():
    if request.method == 'POST':

        searchby = request.form['searchBy']
        daterange = request.form['daterange']

        # Getting date range input
        startDate = daterange.split(" to ")[0]
        endDate = daterange.split(" to ")[1]

        countyPopulations = {'population': [55869,223234,24686,22394,57826,10101,19448,113605,33254,26196,44428,12589,23622,13235,14910,52342,55241,12067,10663,37049,13772,83768,49172,37196,71513,81209,36633,102268,16302,31362,26271,8111,14651,17205,105882,51626,658573,13805,92729,32924,164542,98915,9726,18068,372909,18863,29709,96774,413210,20733,226486,119679,8923,19930,33114,22722,57961,89512,217702,12427,79978,40367,209355,63521,16326,10373,23629,3337,5634,288000,18386,836,2097,4916,96849,2530,2148,31974,58708,13901,12998,8314,1592,108317,10004,9832,7621,3266,6203,8493,1183,6893,9202,2502,579,5230,71887,125922,143476,54018,38837,9498,21108,4485414,212181,110924,1047279,462789,46498,235099,213787,17486,19657,41932,279141,37432,10763,5189,28380,10118,22320,14551,24919,7956,23457,20846,110332,63257,47955,16419,7009,11361,18219,126007,17715,12477,99386,18265,45325,21532,33771,13202,37825,13629,16719,66824,26578,6624,16406,8857,13024,12259,21466,73309,16576,16694,43257,40651,6701,8986,8252,7753,23382,10455,17782,10718,23528,19964,64072,8062,391911,17958,24994,122437,10281,7881,127827,17007,17442,12506,38682,16545,239187,78753,6320,21341,1671329,1129,39752,219186,45905,21547,1153526,27812,192843,999101,28393,135558,181215,18039,900202,152940,64386,30573,10039107,157327,258826,17203,86749,277680,8841,14444,434061,137744,99755,3175692,398329,18807,2470546,1552058,62808,2180085,3338330,881549,762148,283111,766573,446499,1927852,273213,180080,3005,43539,447643,494336,550660,96971,65084,12285,466195,54478,846006,220500,78668,517421,16233,656590,14029,3581,5577,326196,70465,20356,1831,9700,8205,3887,6061,5068,31162,727211,2055,351154,55127,26729,720403,47839,60061,6243,15734,17462,820,6897,1392,582881,1406,7097,8127,56221,356899,14506,5701,22409,154210,769,13283,26183,42758,29068,18278,4952,18845,4265,17767,12172,168424,6324,11267,25638,6824,728,8179,2248,31011,25388,4908,324492,10019,943332,891720,180333,162436,854757,265206,150721,116782,180786,558753,234225,705749,269043,29210,174705,28201,601942,1952778,14105,188910,149657,219252,384902,71686,38001,16826,957755,318316,115081,12125,45660,18582,13811,13639,14428,26937,42022,193920,106221,1471968,19617,159923,46414,14246,8422,367118,770577,293582,41503,8354,18493,403253,365579,161000,2716940,74228,88625,210738,42168,1393452,375751,1496770,553947,974996,724777,74521,264672,328297,184313,433742,471826,132420,44417,21569,15237,553284,33739,74071,25473,18386,8165,11164,3038,44890,19234,83240,107738,16700,19397,153159,12873,19109,15457,39627,79608,22383,24936,6189,54666,10803,119992,67580,13392,289430,10907,24789,258773,128331,2834,292256,6618,760141,43273,45600,156714,17270,148509,12404,22372,16116,26108,26404,759297,20605,13390,87956,146343,10190,4006,64296,19194,22646,10654,26188,114421,98498,244252,23349,1063937,31369,2971,85292,57963,24633,18324,936250,45328,204441,8457,29792,35236,26205,11923,234561,157863,9416,72977,14219,15115,15362,8676,9643,28735,19077,10423,47546,29992,61435,7921,19559,117406,33610,21312,14378,12947,29880,8359,21167,5718,21863,27578,9172,19276,40096,195769,111744,40280,15259,168667,27546,32591,19465,18962,42613,11137,22119,2299,17137,6778,202518,90896,5257,13966,8090,66703,25925,6621,29524,6195,1537,25286,8020,15860,8531,44451,40644,26830,12037,6901,69922,7985,8120,24511,26320,69761,94593,35734,5254,20374,29927,2607,7855,30798,104628,8635,9777,8954,20247,201513,974563,86,72293,167417,481587,4294,87808,6125,9298,46811,23021,7831,45739,119062,12245,2597,1106,229849,7155,24030,845,8756,4315,27511,13876,13099,18112,15179,16667,29871,24412,165697,40108,8027,3838,5366,39907,21039,40408,4531,11823,23951,7681,12882,12142,86878,11392,10194,65435,5761,16426,53544,6578,32628,4739,14305,12147,209689,32304,15441,13184,37562,50621,5150233,18667,10766,104897,15638,19465,922921,17161,6395,34008,21336,12961,38469,34340,4828,12969,51054,8116,17708,3821,6646,48913,27114,56750,9610,37684,21773,21235,12417,532403,109862,128990,49699,696535,108669,15678,34096,35648,28618,29682,307774,171517,104009,44926,262966,37205,11438,13359,13772,12196,15437,34637,28414,33658,14501,50643,179179,20916,16344,15561,4177,5335,5739,31782,15513,141879,259686,23491,194672,6768,4951,21634,5342,44498,131803,16653,75758,11520,16844,13887,16215,13537,55175,690743,66597,282572,38459,35777,379299,83779,8748,11758,67843,15092,20257,37689,118302,26225,32399,10577,33351,49458,26559,43475,114135,42736,206341,23102,78522,16346,22758,19974,33659,65769,31922,338011,78168,40515,170311,47972,82544,36520,44231,33562,20436,32308,27735,158167,36594,79456,39614,485493,109888,45370,129569,964582,46258,10255,35516,148431,38338,70489,13984,47744,5875,19646,20799,16937,19169,12389,170389,25427,12353,37576,24665,28324,16581,271826,23873,44729,20277,22995,34594,20669,10751,195732,15148,7054,181451,15498,107038,30996,8265,62998,28036,65884,28296,24102,33964,7152,3602,13687,12426,5496,25645,131228,26234,25062,21175,19620,14439,9668,20165,12836,18627,42450,11235,11933,9395,16016,17549,46429,16820,93453,9000,7870,17011,38967,17258,97311,9208,19650,15642,10070,6960,8888,12232,10689,14773,10630,16846,14049,19954,9158,9558,6860,16184,19439,37185,18295,151140,20681,10246,14813,33657,226706,11035,8600,11755,16338,22095,33253,39369,15109,10586,8615,7707,9917,42664,13753,5958,15107,8886,25177,6619,490161,93206,18504,4894,9721,172943,11454,34855,97117,16854,6121,12241,7044,34969,51466,21965,6441,35904,10354,19991,103107,7381,12562,12369,7858,16073,4427,25779,14534,9564,66911,2648,3250,19939,2657,1994,8002,8786,8179,1700,34908,38818,2827,18466,7600,122259,2798,2530,28553,6102,36467,33619,25544,31670,2636,2482,7150,5988,1232,5982,2539,5436,34429,3968,1794,13171,19043,2879,602401,3838,7152,2475,19618,1535,81758,2962,9703,2794,33195,28542,11884,9707,4033,34237,5979,31829,5620,2587,10231,16007,2750,5361,15949,3421,5704,6414,5234,24383,9164,2530,61998,4636,9537,74232,4920,3036,6856,54224,4823,516042,21428,176875,2521,5917,3583,4156,2006,5485,22836,7777,2803,6931,1518,5406,2119,8525,3138,165429,19202,21315,22747,7888,44249,12500,26032,133581,19788,46718,30060,8303,12630,20477,81676,12879,12747,39001,93584,4760,10631,26797,16159,70461,36263,19901,10218,8806,6614,101511,12150,7517,14106,323152,14581,35589,50991,5969,8869,17666,25069,37266,26427,10941,35098,8722,110958,26010,18886,19035,45210,16126,4380,44686,13329,766757,54115,22188,166998,14806,31145,14398,60813,15317,7403,9877,21553,13275,24549,9194,27102,8210,65418,17231,9207,92987,12161,19273,31100,11195,17070,28572,6489,21933,10071,10650,28157,13309,30622,46233,7269,23994,66799,10901,4415,14590,25758,57876,12359,64979,2108,16695,24460,17923,57004,49024,18572,19351,25769,12294,14651,8471,14381,132896,12095,20333,12942,36264,7157,26734,62045,25627,126604,21891,40144,37497,13241,127039,240204,203436,9918,6973,9494,15670,19259,27463,440059,6861,19135,33395,20015,22389,69830,32511,15744,432493,31368,244390,97614,14892,46742,140789,10951,24874,38158,390144,153279,23197,21730,129648,8442,20122,23884,47244,53100,10132,21096,42837,82124,53431,49348,260419,134758,4334,110461,22108,59511,47429,46194,38340,26465,10830,15568,13904,108277,67055,295003,30199,54987,122302,39772,34634,57975,152148,16785,35856,50484,39715,31379,207641,70416,579234,827370,92525,33406,168447,102855,163257,31929,259547,29014,255441,325690,19422,1050688,909327,50381,113510,25616,37181,151049,103609,52276,593490,212990,124944,565217,17332,789034,70180,466372,160830,1611699,11399,706775,521202,803907,830622,10405,9108,118081,28405,23324,14883,8209,61550,103126,17766,153401,43517,134159,51787,26143,25276,37349,30950,79595,14029,35784,25239,110268,33415,405813,25449,13975,93088,40711,45605,35684,30981,292406,64697,25127,11066,69872,158510,265066,18038,656955,2116,11853,87607,21761,98451,191995,6229,10799,873972,24558,66699,29144,43453,22780,83156,15118,150500,63888,9328,173566,48980,1257584,26467,20997,5720,23460,8241,24668,291830,12592,24019,190539,159128,60964,41170,8094,68122,52245,75677,367601,1749343,33631,15886,356921,34423,47188,40889,4991,67653,25008,35871,105089,29779,11800,56579,64222,8818,5463,11196,65055,429021,20934,38141,13653,21067,30281,46340,5972,1265843,18600,21491,40596,45130,9846,16337,43199,4298,12229,6623,10641,3740,28887,5639,25474,35893,5527,9336,19683,23222,26277,33386,40062,8194,34274,21629,6375,158293,58746,14119,29579,9126,31364,11249,550321,4055,15170,14548,66972,9315,15165,199070,149013,97238,14865,161075,36649,9805,9266,24664,3259,21627,13682,18612,262440,10897,6207,50484,138377,9709,30693,36953,12297,18174,8259,30628,14361,9947,17103,8210,8988,15541,19316,22124,28065,18636,184945,74897,7713,24500,13586,20758,47632,208080,231840,17010,8064,1327,23390,143617,16383,6990,11128,68098,9742,54019,63343,74125,12586,22786,85436,28183,34153,58595,106272,24573,35294,35252,9775,29118,21018,10417,49587,34192,55535,11973,39288,32174,25126,6792,155271,28124,4321,26658,15916,18336,25110,13809,28321,22015,19383,9632,28815,14286,45381,43909,20183,9689,8630,17955,12108,29690,25343,17712,5143,25388,35789,11754,16172,19443,12133,180463,87364,42478,9020,44743,46305,78871,8679,5982,105780,14349,7426,88595,6797,249948,20387,76745,17709,23920,7561,16878,8278,12547,15573,13185,29131,103967,14706,6571,293086,9850,8352,21824,9544,4403,10001,40117,10125,703011,121328,225081,54062,3959,35723,32708,38355,9776,59013,11920,15227,22837,15117,12088,8697,28530,3617,25619,13180,16132,8644,11551,20627,17076,58236,22092,10529,13615,9174,15805,19136,42339,44573,18302,104418,32149,52607,4696,10309,24748,23018,6270,13288,402022,9397,17894,67215,994205,22761,4660,4902,38280,8166,5930,29025,31952,6089,55928,25398,20563,35649,24730,12873,39592,2013,18289,300576,9453,13319,6681,6237,10725,1252,81366,5635,11402,1690,8613,9140,2846,11050,103806,114434,1258,13753,821,3379,16484,12221,2007,30458,69432,2337,19980,1664,8600,1862,4397,119600,4633,16606,487,3954,5911,1682,6890,1077,43806,10803,11004,8937,12113,3309,34915,9642,3737,6147,4736,696,7396,2126,969,161300,31363,6298,463,745,465,5192,10783,1919,2955,49659,6459,8016,26248,8402,3924,5689,8910,6203,10709,8846,10777,20026,8589,23595,1794,5636,36565,571327,1693,5462,2979,2627,4676,21513,1837,1969,1990,623,2356,61353,9324,3380,922,2762,10067,682,6445,7046,5071,6495,8034,806,3632,8332,319090,34914,748,664,494,35099,7755,4642,3519,6972,4148,16012,2613,2891,9034,7148,33470,5213,10724,7865,1357,14224,187196,21578,35618,17284,5246,3001,1166,5920,5003,722,7224,4158,20729,9385,3487,783,13679,24909,2266715,48905,52778,873,2029,16831,5532,5183,57510,4505,46523,6725,4123,471519,9580,55916,61303,48910,76085,31563,89886,417025,151391,309769,130633,43146,263670,932202,445349,506471,92039,149527,798975,291636,672391,124371,367430,825062,618795,491845,607186,501826,62385,328934,140488,556341,105267,679121,3527,64615,26675,11941,48954,1748,218195,58460,26998,4300,625,4198,71070,19572,19369,23709,71367,4521,67490,8253,38921,18500,146748,123958,27277,150358,10791,16637,32723,15461,4059,76688,305506,46091,1418207,190488,76117,76576,126903,83456,47207,80485,59461,47581,44135,294218,918702,36885,50022,53383,57280,47188,4416,61319,109834,2559903,26296,62914,70941,741770,49221,1356924,1628706,209281,228671,460528,109777,384940,40352,117124,59493,98320,2253858,158714,476143,325789,107740,229863,155299,30999,17807,34016,95379,1476601,75432,48203,102180,177573,63944,61204,89918,967506,39859,24913,169509,37497,11137,24446,27203,17557,46994,18947,32722,142820,261191,90485,216453,82178,10867,69473,22604,159551,74470,28612,13943,11231,97947,55508,102139,335509,27763,37009,167609,42846,58741,321488,51472,382295,69685,224529,11562,8441,60443,21069,537174,50010,135976,62317,117417,23677,55234,4937,181806,43938,209339,9419,61779,55949,86111,45756,35858,21755,22440,1110356,14964,27173,100880,94298,234473,19483,197938,148476,12726,39824,63060,13463,39490,180742,20724,143667,44829,130625,91010,142088,67029,63531,34823,62806,45591,71783,14271,34385,4016,239859,44535,1111761,19731,11580,56177,123131,68412,81801,37667,18069,2216,10415,6832,928,6282,3024,2115,95626,181923,3762,4872,2264,4424,2287,3241,3210,1761,69451,2274,2231,2499,2480,4046,1850,5745,2497,15024,9450,8187,31364,10545,2879,1959,6801,3975,11519,5218,2327,16177,14176,3898,1315,4230,750,31489,1890,20704,2189,8036,10641,67641,3834,37589,27698,102351,53484,97241,65327,45656,67006,43432,383134,26914,38885,134083,206428,41968,101883,36600,41494,1235072,51113,38087,209177,74266,157574,28525,1316756,42126,29898,93649,168937,38875,817473,75783,31365,15040,27006,43161,28264,43960,58266,32413,65325,62322,230149,59463,176862,45672,309833,428348,44731,228683,65093,179746,22907,41172,106987,13654,531687,14508,35328,86215,14424,40525,18672,36134,58457,27772,162466,40882,33861,121154,76666,58518,75314,55178,48590,370606,541013,197974,91987,58988,28275,13085,234602,59911,115710,36692,130817,21772,22194,5702,13758,5311,21859,9429,47995,28762,148306,48111,48657,14672,2137,284014,5495,120749,5666,14142,71522,29003,43009,4891,3859,61056,27711,55834,4333,5712,2653,3688,12627,13279,24530,6002,11085,43538,15765,8708,10073,49853,34877,48011,10253,40474,32832,19596,7629,16931,41100,14073,67997,11131,10076,11993,797434,38465,46963,31127,16376,81784,43654,38284,72592,11096,3583,92459,24258,41569,43143,19983,7250,651552,81289,51527,10916,8793,20211,16124,93053,418187,40224,52354,64487,24404,22925,197692,110980,1912,7199,7393,23382,220944,24658,87487,68238,7869,382067,49962,129749,30571,347818,11603,812855,86085,1780,27036,77950,26835,7208,26682,601592,1332,107100,103009,1216045,64735,163929,47888,421164,121829,60323,628270,187853,130192,4447,64182,162385,524989,38438,79255,38632,64964,84629,253370,278299,566747,29910,269728,129274,7247,155027,14530,36233,45144,84073,43425,24763,209674,545724,85512,141793,369318,317417,113299,40625,109424,46138,170271,830915,18230,305285,90843,46272,1584064,55809,16526,141359,40372,73447,6066,40328,40591,44923,50668,39191,206865,51361,348899,26794,449058,48479,164292,82082,638931,125577,24527,170872,8688,202558,14066,20866,192122,227907,14553,411406,57300,32244,45650,33745,37677,66618,30479,162809,27260,22347,138293,62680,523542,70811,19222,354081,30073,66551,98012,67493,16828,298750,9463,30657,26118,38440,79546,86175,126884,415759,20473,319785,106721,27316,30368,280979,2751,18453,3365,6901,35077,38839,5297,1962,10429,1376,9292,3736,14070,28009,4086,8972,19775,5424,4351,5892,2921,3829,6713,2299,7052,4185,1899,6164,3191,3453,1298,17526,7291,1301,3344,2013,903,4939,12797,25844,61128,3781,5586,2379,4935,28332,2061,2216,193134,6576,14177,113775,2865,2153,10394,2344,6376,3098,1391,10177,5441,8384,15932,5435,22814,2756,76978,49713,16160,15064,133088,108110,39842,14678,27767,56391,40667,17297,31959,7615,36004,56520,14230,60520,694144,11663,20490,53948,37159,41133,18523,42208,49133,29464,23320,69069,13427,64934,367804,6620,25050,25652,56786,17304,28117,32345,25178,8201,18582,11786,54495,17788,470313,7016,25633,44142,12268,34366,54068,53794,25694,24602,97984,28907,34375,96387,12422,46545,208993,6488,21403,30069,22241,8076,5048,16832,80245,33167,53382,71813,332285,22068,15026,98250,937166,20157,13715,158348,191283,61599,11284,17883,19972,5872,41277,129375,16673,33328,27345,238412,144657,57735,18705,86715,23510,8553,1887,51153,30032,7000,23112,88723,3509,32565,362924,2003554,11931,654,18685,93245,374264,229211,9203,1546,7093,37864,18443,48155,43664,21290,13943,423163,13094,5926,30026,7530,43837,52646,7306,10471,2853,3387,8175,1034730,2920,21493,156209,13635,2726,41257,75951,1398,4797,3464,5737,2171,7287,2635516,12728,18546,5331,887207,20160,2211,10124,3278,11157,18360,166223,1932,184826,839238,42698,17297,35514,25346,3830,5712,1155,811688,10725,19717,20306,21492,342139,6229,26988,1409,7658,20837,21886,136212,123945,28880,166847,33406,2964,8461,5399,3933,57602,4713325,66553,5576,5658,230191,3819,82737,868707,36649,23021,61643,37084,22968,36664,4886,98594,20938,1536,8935,14760,35529,2274,251565,5200,40482,175817,20083,15601,136154,47431,404,762,52600,4337,272,3667,30680,3664,49859,12893,21428,7520,20154,17239,17404,88219,23437,3233,12207,21795,169,310569,5951,7984,256623,743,14284,9854,5771,4274,36643,58722,51584,2138,176832,24823,4873,8545,19818,607391,20940,12388,1200,65204,50113,13595,14714,362294,9836,2112,83396,29189,23194,142878,9605,15823,51353,117415,6704,12514,137713,3849,3452,12023,15976,6948,854,17074,104915,10264,54406,10542,8237,28859,66730,6055,2793,16703,3265,25274,3022,232751,9128,64633,9366,1291,1350,3776,7397,2102515,138034,776,12337,1501,32750,119200,1273954,14651,21672,41753,3657,26741,49025,56590,92084,72971,55246,11998,35882,276652,41556,5056,132230,12769,21358,590551,51070,8010,69984,45539,8713,18010,14179,11840,6710,56046,128289,20463,950,355481,19938,10012,5051,9754,54839,12017,7886,13188,12124,1479,2483,1160437,15308,30939,21620,42145,72259,35734,636235,34091,177556,2711,260213,36777,35470,29993,163774,6163,49402,7235,25362,28892,27037,58191,58409,42222,55062,32316,109330,14860,13145,31605,15911,236842,75558,4147,78997,6280,33419,16231,21004,17148,54885,30725,29791,6963,11880,352802,14619,5131,52605,9932,14318,28544,10953,1147532,71222,15749,27270,56042,89313,16720,37348,23753,15550,19819,11336,33911,107766,330818,50557,2190,37109,76523,7025,26836,17148,10603,23423,413538,37591,12196,13261,8834,30587,10582,98535,14930,23091,11710,12095,15232,37051,23902,17608,60354,29652,22802,38353,470335,34027,7370,9023,94186,22573,81948,26586,21566,43616,30104,17631,136215,152882,6422,11159,40595,40164,53740,18015,37383,28684,68280,159428,16762,6478,47266,244835,17370,5538,40044,5346,24019,14617,7967,29036,6347,134510,53016,22529,7446,82168,41085,17478,12554,179225,242742,3981,31346,12271,94398,18249,230436,99143,25301,24932,92108,449974,22630,14954,28078,19983,22582,204390,77200,77331,488241,3985,110593,43429,7627,95222,2225,97733,75061,85141,32221,2252782,271473,47935,22425,80707,10939,66768,42243,22471,13724,904980,17582,129205,12083,822083,522798,45723,290536,4488,60760,229247,50104,250873,16441,119171,21457,13957,21939,91945,7109,8508,8448,42406,7823,11568,34662,23175,28810,13776,67256,28576,57146,178124,15907,20409,32019,17624,56072,30531,26516,58758,26868,23424,105612,13275,17884,24496,41411,6969,7460,8247,33432,56450,73361,28695,9554,13688,12573,16695,6839,8591,24176,39402,8114,15065,5821,83518,20394,20220,15562,45244,15036,264542,13031,15414,50089,64658,34774,57532,16131,546695,87839,27668,43150,45368,104646,4295,103403,9004,51439,36960,18913,23678,5687,20643,84769,26687,169561,20434,118016,16665,19189,27593,78981,135692,40350,15574,4556,945726,46253,37930,35595,187885,89221,7287,42754,43783,70772,13351,196311,17252,163354,14178,90687,64442,16558,40899,115340,20343,29649,30822,22195,103868,15720,136034,404198,50990,24443,171907,72999,38880,11790,46341,14800,13822,7584,39261,13211,4413,8445,99500,19830,79858,2356,29194,8393,30485,9831,42343,23464,20226,7805,6927]}
        countyPopulations = pd.DataFrame(data=countyPopulations)

        if searchby == 'Cases' or searchby == 'Cases per 100,000':
            caseData = getCountyCaseData()
            caseData = caseData.drop(['County Name', 'State'], axis=1)
            for key in caseData.keys():
                if key < startDate or key > endDate:
                    caseData = caseData.drop([key], axis=1)
            if caseData.empty:
                return render_template('datavisualizationstate.html', invalidmessage="Error. Invalid date range.")
            caseData['Value'] = caseData.iloc[:, -1] - caseData.iloc[:, 0]
            countyId = getCountyFIPS()
            data = pd.concat([countyId, caseData['Value']], axis=1, keys=['countyFIPS', 'Value'])
            if searchby == 'Cases per 100,000':
                data['Value'] = (data['Value'] / countyPopulations['population']) * 100000
        else:
            deathData = getCountyDeathData()
            deathData = deathData.drop(['County Name', 'State'], axis=1)
            for key in deathData.keys():
                if key < startDate or key > endDate:
                    deathData = deathData.drop([key], axis=1)
            if deathData.empty:
                return render_template('datavisualizationstate.html', invalidmessage="Error. Invalid date range.")
            deathData['Value'] = deathData.iloc[:, -1] - deathData.iloc[:, 0]
            countyId = getCountyFIPS()
            data = pd.concat([countyId, deathData['Value']], axis=1, keys=['countyFIPS', 'Value'])
            if searchby == 'Deaths per 100,000':
                data['Value'] = (data['Value'] / countyPopulations['population']) * 100000


        # Create map
        m = folium.Map(width=1000, height=600, location=[39.8283, -98.5795], zoom_start=4)
        with open("us-counties.json", "r") as configJSON:
            high_res_county_geo = json.load(configJSON)

        # Counties that have a negative number as their value will be set to 0 as their new value
        data.loc[data['Value'] <= 0, 'Value'] = 0

        m.choropleth(
            geo_data=high_res_county_geo,
            name='choropleth',
            data=data,
            columns=['countyFIPS', 'Value'],
            key_on='properties.GEO_ID',
            fill_color="YlOrRd",
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=searchby
        )

        style_function = lambda x: {'fillColor': '#ffffff', 
                                    'color':'#000000', 
                                    'fillOpacity': 0.1, 
                                    'weight': 0.05}
        highlight_function = lambda x: {'fillColor': '#000000', 
                                        'color':'#000000', 
                                        'fillOpacity': 0.50, 
                                        'weight': 0.05}

        for county in high_res_county_geo['features']:
            county['properties']['Value'] = str(data.loc[data['countyFIPS'] == county['properties']['GEO_ID'], 'Value'].values)

        NIL = folium.features.GeoJson(
            high_res_county_geo,
            style_function=style_function,
            control=False,
            highlight_function=highlight_function,
            tooltip=folium.features.GeoJsonTooltip(
                fields=["NAME", "Value"],
                aliases=['', ''],
                style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;") 
            )
        ).add_to(m)

        m.add_child(NIL)
        m.keep_in_front(NIL)


        folium.LayerControl().add_to(m)
        m.save("templates/map.html")
        return render_template('datavisualizationcounty.html', searchby=searchby, daterange=daterange)
    else:
        return render_template('datavisualizationcounty.html')

@app.route('/map')
def loadmap():
    return render_template('map.html')

@app.route('/emptymap')
def emptymap():
    m = folium.Map(width=1000, height=600, location=[39.8283, -98.5795], zoom_start=4)
    m.save("templates/emptymap.html")
    return render_template('emptymap.html')