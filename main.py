# imports
import pandas as pd
from sodapy import Socrata
from flask import Flask, render_template, request, redirect
from IPython.display import HTML
from numpy import math
import numpy as np
app = Flask(__name__)

# This function returns a dataframe of the most recent covid data


def getData():
    # Importing data set to client variable
    client = Socrata("data.cdc.gov", None)
    results = client.get("9mfq-cb36", limit=23000)

    # Convert to pandas DataFrame so we can work with the dataset
    results_df = pd.DataFrame.from_records(results)

    # Removing unhelpful columns
    results_df = results_df.drop(
        ['consent_cases', 'consent_deaths', 'created_at'], 1)
    # Removing rows with NaN values
    #results_df = results_df.dropna()

    # Converting date column from string to datetime object
    results_df['submission_date'] = pd.to_datetime(
        results_df['submission_date'])
    results_df['submission_date'] = results_df['submission_date'].dt.strftime(
        '%Y-%m-%d')

    # Sorting dataframe so that most recent submissions are first
    results_df = results_df.sort_values(by='submission_date', ascending=False)

    # Exporting to csv file
    results_df.to_csv('data.csv', header=True, index=False)

    return results_df


@app.route('/')
def homefunc():
    return render_template('home.html')


@app.route('/datasearch', methods=['GET', 'POST'])
def datafunc():

    if request.method == 'POST':

        state = request.form['state']
        if state != "None":
            data = getData()
            data = data[data['state'] == state]
        else:
            data = getData()
            pass


        data = data.fillna(0)
        data[["tot_cases", "conf_cases", "prob_cases", "new_case",
                            "pnew_case", "tot_death", "conf_death",
                            "prob_death", "new_death", "pnew_death"]] = data[["tot_cases",
                            "conf_cases", "prob_cases", "new_case",
                            "pnew_case", "tot_death", "conf_death",
                            "prob_death", "new_death", "pnew_death"]].astype('float')
        data[["tot_cases", "conf_cases", "prob_cases", "new_case",
                            "pnew_case", "tot_death", "conf_death",
                            "prob_death", "new_death", "pnew_death"]] = data[["tot_cases",
                            "conf_cases", "prob_cases", "new_case",
                            "pnew_case", "tot_death", "conf_death",
                            "prob_death", "new_death", "pnew_death"]].astype('int')


        check = request.form.get('defaultCheck1')
        if check == "yes":
            data = data.groupby(['state']).first().reset_index()
        else:
            pass

        check2 = request.form.get('defaultCheck2')

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
        data["conf_cases"] = data.conf_cases.apply(lambda x : "{:,}".format(x))
        data["prob_cases"] = data.prob_cases.apply(lambda x : "{:,}".format(x))
        data["new_case"] = data.new_case.apply(lambda x : "{:,}".format(x))
        data["pnew_case"] = data.pnew_case.apply(lambda x : "{:,}".format(x))
        data["tot_death"] = data.tot_death.apply(lambda x : "{:,}".format(x))
        data["conf_death"] = data.conf_death.apply(lambda x : "{:,}".format(x))
        data["prob_death"] = data.prob_death.apply(lambda x : "{:,}".format(x))
        data["new_death"] = data.new_death.apply(lambda x : "{:,}".format(x))
        data["pnew_death"] = data.pnew_death.apply(lambda x : "{:,}".format(x))

        data = data.rename(columns={"submission_date": "Date", "state": "State", "tot_cases": "Total Cases",
                            "conf_cases": "Confirmed Cases", "prob_cases": "Probable Cases", "new_case": "New Cases",
                            "pnew_case": "Probable New Cases", "tot_death": "Total Deaths", "conf_death": "Confirmed Deaths",
                            "prob_death": "Probable Deaths", "new_death": "New Deaths", "pnew_death": "Probable New Deaths"})


        return render_template('datasearch.html', dataColumns=data.keys(), dataItems=data.to_numpy(), check2=check2)
    else:
        return render_template('datasearch.html')


@app.route('/datavisualization')
def searchfunc():
    return render_template('datavisualization.html')
