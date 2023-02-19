"""
    This is a simple example of how to use the withings_api library.
    The scope of this example is to show how to get the credentials,
    make a call to the API and save the measurements in a .csv file.
    To get the example working you need to:
    0. create a Withings account and get your client_id and consumer_secret
    1. install withings_api with: pip install withings-api

    @author: Andrea Efficace, Loreno Rossi
"""
import os
from os import path
import pickle
from typing import cast
from oauthlib.oauth2 import MissingTokenError
from withings_api import WithingsAuth, WithingsApi, AuthScope
from withings_api.common import MeasureType, GetSleepField, \
    MeasureGetMeasGroupCategory, CredentialsType, GetActivityField, GetSleepSummaryField
import pandas as pd
import arrow
# Function to create a dataframe from the data array
def create_df_from_data(data):
    df=pd.DataFrame()
    for d in data:
        df=pd.concat([df, pd.DataFrame(d.__dict__, index=[0])], ignore_index=True)
    return df
# function to get start date and end date from gg/mm/yyyy using arrow library
def get_date(date):
    return arrow.get(date, 'DD/MM/YYYY')
# Path to the file where the credentials will be saved to avoid the 2FA procedure or
# temporary suspension of the account
CREDENTIALS_FILE = path.abspath(
    path.join(path.dirname(path.abspath(__file__)), "..\.credentials")
)
print(CREDENTIALS_FILE)
# Function to save the credentials in a file
def save_credentials(credentials: CredentialsType) -> None:
    """Save credentials to a file."""
    print("Saving credentials in:", CREDENTIALS_FILE)
    with open(CREDENTIALS_FILE, "wb") as file_handle:
        pickle.dump(credentials, file_handle)

# Function to load the credentials from a file
def load_credentials() -> CredentialsType:
    """Load credentials from a file."""
    print("Using credentials saved in:", CREDENTIALS_FILE)
    with open(CREDENTIALS_FILE, "rb") as file_handle:
        return cast(CredentialsType, pickle.load(file_handle))

# Create an auth object with your Withings credentials (needed for 2FA).
# Secrets should be stored in a secure location and not in your code.

# Developer Account information

client_id = "9694b7164bdb2c898f48d343f4fcfb15eac7827323dc9027a7de73634d82c070"
consumer_secret = "0e969c5b4cdfb0743d952b58c4ff444209e0df5c08b377d89383fefbf5701ebd"
# The callback URI is used to get the authorization code. It redirects all the request to
# withigns API at the end of the 2FA procedure to the localhost:5000. "5000" is the port
# that it was set in the developer dashboard.
callback_uri = "https://localhost:5000"

# Create the auth object with the credentials and the scope of the data that you want to get.
# This class is used to manage the 2FA procedure and all the request to the API.
auth = WithingsAuth(
    client_id=client_id,
    consumer_secret=consumer_secret,
    callback_uri=callback_uri,
    scope=(
        AuthScope.USER_ACTIVITY,
        AuthScope.USER_METRICS,
        AuthScope.USER_INFO,
        AuthScope.USER_SLEEP_EVENTS,
    ),
)

# Before making any call to the API, you need to get the credentials: if the credentials are
# already saved in a file, the script will load them, otherwise it will start the 2FA procedure.
# This procedure is needed to avoid any type of abuse of the API.
if path.isfile(CREDENTIALS_FILE):
        print("Attempting to load credentials from:", CREDENTIALS_FILE)
        api = WithingsApi(load_credentials(), refresh_cb=save_credentials)
        api.refresh_token()
        try:
            api.user_get_device()
        except MissingTokenError:
            os.remove(CREDENTIALS_FILE)
            print("Credentials in file are expired. Re-starting auth procedure...")

if not path.isfile(CREDENTIALS_FILE):
    print("Attempting to get credentials...")
    authorize_url = auth.get_authorize_url()
    print("Open this URL in your browser:", authorize_url)
    auth_code = input("Enter the code from the browser: ")
    # get the credentials
    credentials = auth.get_credentials(auth_code)
    save_credentials(credentials)
    api = WithingsApi(load_credentials(), refresh_cb=save_credentials)


# Interval of time to get data from
sd = input("Start date (DD/MM/YYYY): ")
ed = input("End date (DD/MM/YYYY): ")
start_date = get_date(sd)
end_date = get_date(ed)

# Procedure to get all avaiable measurements from the API.
# The measurements are saved in a dictionary with the name of the measurement as key.
# Each measurement is saved in a .csv file with the name of the measurement as file name.
# Each query to the API contains:
# attrib:
# category: 1 for all the measurements, 0 for user objectives
# created: date of creation of the measurement
# date: date of the measurement
# deviceid : id of the device used to get the measurement
# grpid :   id of the group of measurements
# measures : array of measurements (value, unit)
df_dict= {}
# Getting all the available measurements types like weight, height, etc.
# Each data query is parsed and saved in a dataframe.
measurements = api.measure_get_meas(startdate=start_date, enddate=end_date)
measure_types = [getattr(MeasureType, attr) for attr in dir(MeasureType) if not callable(getattr(MeasureType, attr)) and not attr.startswith("__") and not attr=='UNKNOWN']

for measure_type in measure_types:
    response = api.measure_get_meas(meastype=measure_type,
                                    category=MeasureGetMeasGroupCategory(1),
                                    startdate=start_date,
                                    enddate=end_date,
                                    offset=0,
                                    lastupdate=None
                                    )
    if response.measuregrps:
        dfdata=response.measuregrps
        column = response.measuregrps[0].__fields_set__
        df_data = create_df_from_data(dfdata)
        df_data['measures'] = df_data['measures'].apply(lambda x:getattr(x,'value')*10**getattr(x,'unit'))
        df_dict[str(measure_type).split('.')[1]] = df_data
        # delete .csv files if they already exist
        if path.isfile(str(measure_type).split('.')[1]+".csv"):
            os.remove(str(measure_type).split('.')[1]+".csv")
        df_data.to_csv(str(measure_type).split('.')[1]+".csv", index=False)

# Activity measurements
activity_measure = api.measure_get_activity(data_fields=GetActivityField,
                                            offset=0,
                                            startdateymd=start_date,
                                            enddateymd=end_date)

# Creating Dataframes to store the data
activity_data = activity_measure.activities
columns = list(activity_data[0].__fields_set__)
activity_df = create_df_from_data(activity_data)
if path.isfile("ACTIVITY_DATA.csv" + ".csv"):
    os.remove("ACTIVITY_DATA.csv" + ".csv")
# Storing in a .csv file the data
activity_df.to_csv("ACTIVITY_DATA.csv", index=False)

# ECG measurements
heart_measure = api.heart_list(startdate=start_date, enddate=end_date)
heart_columns = list(heart_measure.series[0].__fields_set__)
heart_columns.append('ecg')
heart_data = heart_measure.series
heart_df = pd.DataFrame(heart_measure.series,columns = heart_columns)
# cancellare heart_data.csv se esiste all'interno della cartella
if path.isfile("HEART_DATA.csv"):
    os.remove("HEART_DATA.csv")
heart_df.to_csv("HEART_DATA.csv", index=False)

# Sleep measurements are taken for the current month
sleep_measure = api.request(path="v2/sleep",
                            params={"action":"getsummary",
                                    "startdateymd": arrow.utcnow().shift(days=-arrow.utcnow().date().day+1).format('YYYY-MM-DD'),
                                    "enddateymd": arrow.utcnow().format("YYYY-MM-DD")})
sleep_df = pd.DataFrame(sleep_measure['series'])
if path.isfile("SLEEP_DATA.csv"):
    os.remove("SLEEP_DATA.csv")
sleep_df.to_csv("SLEEP_DATA.csv", index=False)
