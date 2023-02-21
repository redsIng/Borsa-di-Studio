"""
    This is a simple example of how to use the withings_api library.
    The scope of this example is to show how to get the credentials,
    make a call to the API and save the measurements in a .csv file.
    To get the example working you need to:
    0. create a Withings account and get your client_id and consumer_secret
    1. install withings_api with: pip install withings-api in your virtual environment
    (If you are using Anaconda:
    1.1. create a virtual environment with: conda create -n your_env_name python=3.7
    1.2. activate the virtual environment with: conda activate your_env_name
    1.3. install withings_api with: pip install withings-api
    If you are using Jupyter Notebook:
    1.1. Insert the following code in a cell:!pip install withings-api)

    @author: Andrea Efficace, Loreno Rossi
"""
import os
from os import path
import pickle
from typing import cast
from wsgiref import headers

import requests
from _cffi_backend import callback
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
start_datetm = int(start_date.timestamp())
end_datetm = int(end_date.timestamp())
import time
import datetime
start_date = datetime.date(2023,2,1)
end_date = datetime.date(2023,2,12)

unixtime = time.mktime(start_date.timetuple())
unixtime1 = time.mktime(end_date.timetuple())
#url = f'https://wbsapi.withings.net/v2/rawdata?action=get&hash_deviceid=2e11be304313d1e525e09392971dddec7e46a0d8&rawdata_type=1&startdate={unixtime}&enddate={unixtime1}'
# &startdateymd={start_date}&enddateymd={start_date}
#url = f'https://wbsapi.withings.net/v2/measure?action=getintradayactivity&startdateymd={start_date}&enddateymd={end_date}&access_token={api.get_credentials().access_token}&appi_d={client_id}&appi_secret={consumer_secret}&data_fields=heart_rate'
url = f'https://wbsapi.withings.net/v2/measure?action=getintradayactivity&startdate={unixtime}&enddate={unixtime1}&data_fields=heart_rate&access_token={api.get_credentials().access_token}'
url = f'https://wbsapi.withings.net/v2/rawdata?action=get&hash_deviceid=2e11be304313d1e525e09392971dddec7e46a0d8&rawdata_type=1&startdate={unixtime}&enddate={unixtime1}'
response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    # Stampa i dati di misurazioni raw HR
    for measure in data['body']['measuregrps']:
        for measure_type in measure['measures']:
            if measure_type['type'] == 16:
                print(f"Timestamp: {measure['date']} - Raw HR: {measure_type['value']}")
else:
    print("Errore nella richiesta delle misurazioni raw HR")





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
measurements = api.measure_get_meas(startdate=start_date, enddate=end_date,offset=0,
                                    lastupdate=None)
api.request(path="/v2/user",params={"action":"getdevice"})

api.notify_list()
# function to get unix timestamp from date hour minute second

def get_timestamp(date,hour,minute,second):
    return arrow.get(date, 'DD/MM/YYYY').replace(hour=hour, minute=minute, second=second).timestamp

start_datetm = get_timestamp("10/02/2023",9,40,0)
end_datetm = get_timestamp("11/02/2023",13,00,00)
# get unix timestamp from date DD-MM-YYYY HH:MM:SS
std = arrow.get("10/02/2023", 'DD/MM/YYYY').replace(hour=9, minute=40, second=0).timestamp
etd = arrow.get("11/02/2023", 'DD/MM/YYYY').replace(hour=9, minute=40, second=0).timestamp



d = datetime.date(2023,2,10)
d1 = datetime.date(2023,2,11)

unixtime = time.mktime(d.timetuple())
unixtime1 = time.mktime(d1.timetuple())
response = api.measure_get_meas(meastype=MeasureType.WEIGHT,
                                    category=MeasureGetMeasGroupCategory(1),
                                    startdate=start_date,
                                    enddate=end_date,
                                    offset=0,
                                    lastupdate=None
                                    )
api.request("measure",params={"action":'getmeas',"meastype":[1,4,5,6,8,9,10,11,12,54,71,73,76,77,88,91,123,135,136,137,138,139]})
api.request("measure",params={"action":'getworkouts',"lastupdate":int(unixtime)})


'''
raw_data = api.request("v2/rawdata",params={"action":'get',
                                                 "hash_deviceid":'2e11be304313d1e525e09392971dddec7e46a0d8',
                                                 "rawdata_type":1,
                                                 "startdate":1676806891,
                                                 "enddate":1676806891})
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

# data in unix timestamp

sleep = api.sleep_get(data_fields=GetSleepField,startdate=arrow.utcnow().shift(days=-arrow.utcnow().date().day+1).format('YYYY-MM-DD')
              , enddate=arrow.utcnow().format('YYYY-MM-DD'))

'''
while 1:
    notify1=api.notify_get(callbackurl= callback_uri)
    print(notify1)
    notify2=api.notify_subscribe(callbackurl= callback_uri)
    print(notify2)











