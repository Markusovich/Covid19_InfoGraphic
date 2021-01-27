#imports
import pandas as pd
from sodapy import Socrata
from flask import Flask, render_template, request, redirect
from IPython.display import HTML 
app = Flask(__name__)

def getData():
    # Importing data set to client variable
    client = Socrata("data.cdc.gov", None)
    results = client.get("9mfq-cb36", limit=22000)

    # Convert to pandas DataFrame so we can work with the dataset
    results_df = pd.DataFrame.from_records(results)

    # Removing unhelpful columns
    results_df = results_df.drop(['consent_cases', 'consent_deaths', 'created_at'], 1)
    # Removing rows with NaN values
    results_df = results_df.dropna()

    # Converting date column from string to datetime object
    results_df['submission_date'] = pd.to_datetime(results_df['submission_date'])
    results_df['submission_date'] = results_df['submission_date'].dt.strftime('%Y-%m-%d')

    # Sorting dataframe so that most recent submissions are first
    results_df = results_df.sort_values(by='submission_date', ascending=False)

    # Exporting to csv file
    results_df.to_csv('data.csv', header=True, index=False)

    return results_df


@app.route('/')
def homefunc():
    return render_template('home.html')

@app.route('/exportdata', methods=['GET', 'POST'])
def datafunc():

    if request.method == 'POST':
        if request.form['state'] != "None":
            state = request.form['state']
            data = getData()
            data = data[data['state'] == state]
        else:
            data = getData()

        data.reset_index(drop=True, inplace=True)

        return render_template('exportdata.html', data=data.to_html())
    else:
        return render_template('exportdata.html')

@app.route('/search')
def searchfunc():
    return render_template('search.html')
