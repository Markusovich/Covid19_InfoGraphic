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
matplotlib.use('Agg')
app = Flask(__name__)

# This is so that the correct graphs get displayed, not older graphs
# Resets cache after every run
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

# This function returns a dataframe (dataset) of the most recent covid data
# Everytime your run the project, a new dataset is always pulled from data.cdc.gov
def getData():
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
            data = getData()
            data = data[data['state'] == state]
        else:
            data = getData()
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
def searchfunc():
    return render_template('datavisualization.html')
