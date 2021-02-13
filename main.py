# imports
import pandas as pd
from sodapy import Socrata
from flask import Flask, render_template, request, redirect
from IPython.display import HTML
from numpy import math
import numpy as np
import matplotlib.pyplot as plt
app = Flask(__name__)

# This function returns a dataframe of the most recent covid data


def getData():
    # Importing data set to client variable
    client = Socrata("data.cdc.gov", None)
    results = client.get("9mfq-cb36", limit=100000)

    # Convert to pandas DataFrame so we can work with the dataset
    results_df = pd.DataFrame.from_records(results)

    # Removing unhelpful columns
    results_df = results_df.drop(
        ['consent_cases', 'consent_deaths', 'created_at', 'conf_cases', 'prob_cases', 'pnew_case', 'conf_death', 'prob_death', 'pnew_death'], 1)
    # Removing rows with NaN values
    #results_df = results_df.dropna()

    # Converting date column from string to datetime object
    results_df['submission_date'] = pd.to_datetime(
        results_df['submission_date'])
    results_df['submission_date'] = results_df['submission_date'].dt.strftime(
        '%Y-%m-%d')

    # Sorting dataframe so that most recent submissions are first
    results_df = results_df.sort_values(by='submission_date', ascending=False)

    return results_df


@app.route('/')
def homefunc():
    return render_template('home.html')


@app.route('/datasearchstate', methods=['GET', 'POST'])
def datafunc():

    if request.method == 'POST':

        state = request.form['state']
        if state != "None":
            data = getData()
            data = data[data['state'] == state]
        else:
            data = getData()
            pass

        daterange = request.form['daterange']
        daterange = daterange.split(" to ")
        startDate = daterange[0]
        endDate = daterange[1]
        data = data[data.submission_date >= startDate]
        data = data[data.submission_date < endDate]

        data = data.fillna(0)
        data[["tot_cases", "new_case", "tot_death", "new_death"]] = data[["tot_cases", "new_case", "tot_death", "new_death"]].astype('float')
        data[["tot_cases", "new_case", "tot_death", "new_death"]] = data[["tot_cases", "new_case", "tot_death", "new_death"]].astype('int')

        data.reset_index(drop=True, inplace=True)

        shuffle = request.form['shuffle']
        if shuffle != "None":
            for i in data.keys():
                if shuffle == str(i):
                    data = data.sort_values(by=[shuffle], ascending=False)
                    break
        else:
            pass

        data["tot_cases"] = data.tot_cases.apply(lambda x : "{:,}".format(x))
        data["new_case"] = data.new_case.apply(lambda x : "{:,}".format(x))
        data["tot_death"] = data.tot_death.apply(lambda x : "{:,}".format(x))
        data["new_death"] = data.new_death.apply(lambda x : "{:,}".format(x))

        data = data.rename(columns={"submission_date": "Date", "state": "State", "tot_cases": "Total Cases",
                            "new_case": "New Cases",
                            "tot_death": "Total Deaths",
                            "new_death": "New Deaths",})



        post = "This is a post"
        return render_template('datasearchstate.html', dataColumns=data.keys(), dataItems=data.to_numpy(), post=post)
    else:
        return render_template('datasearchstate.html')


@app.route('/datavisualization')
def searchfunc():
    return render_template('datavisualization.html')
