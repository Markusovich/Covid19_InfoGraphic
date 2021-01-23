#imports
import pandas as pd
from sodapy import Socrata

# Unauthenticated client only works with public data sets. Note 'None'
# in place of application token, and no username or password:
client = Socrata("data.cdc.gov", None)

# Max results, returned as JSON from API / converted to Python list of
# dictionaries by sodapy.
results = client.get("9mfq-cb36", limit=22000)
# Convert to pandas DataFrame
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
print(results_df)
