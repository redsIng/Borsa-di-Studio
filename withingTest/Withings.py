import pickle
from numpy import NaN
import requests
import withings_api
import os
import pandas as pd
from os import path
import arrow
from oauthlib.oauth2 import MissingTokenError
from withings_api import CredentialsType, AuthScope
import time
import datetime
from typing import cast, Final


class Withings(withings_api.WithingsAuth):
    pass

    client_id = "YOUR_CLIENT_ID"
    consumer_secret= "consumer_secret"
    callback_uri = "http://localhost:8080"
    access_token = "access_token"
    credential_file = path.abspath(
        path.join(path.dirname(path.abspath(__file__)), "..\.credentials")
    )
    scope=(
        AuthScope.USER_ACTIVITY,
        AuthScope.USER_METRICS,
        AuthScope.USER_INFO,
        AuthScope.USER_SLEEP_EVENTS,
    )
    api = None
    MAIN_URL: Final= "https://wbsapi.withings.net"




    def __init__(self, consumer_key, consumer_secret, callback_uri):
            self.client_id = consumer_key
            self.consumer = consumer_secret
            self.callback_uri = callback_uri
            super().__init__(client_id = self.client_id,
                             consumer_secret = self.consumer,
                             callback_uri = self.callback_uri,
                             scope = self.scope)

    def authorize(self):
        if path.isfile(self.credential_file):
            print("Attempting to load credentials from:", self.credential_file)
            self.api = withings_api.WithingsApi(self.load_credentials(), refresh_cb=self._save_credentials_)
            self.api.refresh_token()
            try:
                self.api.user_get_device()
            except MissingTokenError:
                os.remove(self.credential_file)
                print("Credentials in file are expired. Re-starting auth procedure...")

        if not path.isfile(self.credential_file):
            print("Attempting to get credentials...")
            authorize_url = self.auth.get_authorize_url()
            print("Open this URL in your browser:", authorize_url)
            auth_code = input("Enter the code from the browser: ")
            # get the credentials
            credentials = self.auth.get_credentials(auth_code)
            self.save_credentials(credentials)
            self.api = withings_api.WithingsApi(self.load_credentials(), refresh_cb=self._save_credentials_)
        self.access_token = self.api.get_credentials().access_token
        self.device_options()

    def _save_credentials_(self,credentials: CredentialsType) -> None:
        """Save credentials to a file."""
        # print the attribute credential_file of the class
        print("Saving credentials to:", self.credential_file)
        with open(self.credential_file, "wb") as file_handle:
            pickle.dump(credentials, file_handle)

    def load_credentials(self) -> CredentialsType:
        """Load credentials from a file."""
        print("Using credentials saved in:", self.credential_file)
        with open(self.credential_file, "rb") as file_handle:
            return cast(CredentialsType, pickle.load(file_handle))

    def device_options(self):
        self.devices=pd.DataFrame(self.api.user_get_device().devices, columns=['type', 'model', 'battery', 'deviceid', 'timezone'])
        # substitue each cell wirh the column value of the tuple
        self.devices['type'] = self.devices['type'].apply(lambda x: x[1])
        self.devices['model'] = self.devices['model'].apply(lambda x: x[1])
        self.devices['battery'] = self.devices['battery'].apply(lambda x: x[1])
        self.devices['deviceid'] = self.devices['deviceid'].apply(lambda x: x[1])
        self.devices['timezone'] = self.devices['timezone'].apply(lambda x: x[1])

    def create_df_from_data(self, data):
        df = pd.DataFrame(data)
        df = pd.concat([df.drop(['data'], axis=1), df['data'].apply(pd.Series)], axis=1)
        return df

    def get_unix_timestamp(self, datetime):
        # convert datetime.date to timestamp with time 00:00:00
        return time.mktime(datetime.timetuple())



    # convert unix timestamp to datetime with hour and minute and second
    def get_date_from_timestamp(self, timestamp):
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    # function to get meastype from int
    def get_meastype(self, meastype):
        meastype_dict = {1: 'weight', 4: 'height', 5: 'fat_free_mass', 6: 'fat_ratio', 8: 'fat_mass_weight',
                            9: 'diastolic_blood_pressure',
                         10: 'diastolic_blood_pressure', 11: 'systolic_blood_pressure', 12: 'heart_pulse',
                         54: 'temperature', 71: 'sp02', 73: 'skin_temperature', 76: 'muscle_mass', 77: 'hydration',
                         88: 'pulse_wave_velocity', 91: 'bone_mass', 123: 'pulse_wave_velocity_imt', 135: 'heart_rate_variability',
                         136: 'heart_rate_variability_sdnn', 137: 'heart_rate_variability_rmssd', 138: 'heart_rate_variability_pnn50',
                         139: 'heart_rate_variability_pnn20'}
        return meastype_dict[meastype]

    # function to get the device model from the deviceid in dataframe self.devices
    def get_device_model(self, deviceid):
        if deviceid == None:
            return 'Withings'
        return self.devices[self.devices['deviceid'] == deviceid]['model'].values[0]

    def get_measure(self, start_date, end_date):
        url = f'https://wbsapi.withings.net/measure?action=getmeas&startdate' \
              f'={self.get_unix_timestamp(start_date)}&' \
              f'enddate={self.get_unix_timestamp(end_date)}&' \
              f'meastype=1,4,5,6,8,10,11,12,54,71,73,76,77,88,91,123,135,136,137,138,139&' \
              f'access_token={self.api.get_credentials().access_token}'

        response = requests.get(url)
        # list of string of all meastype
        meastype_list = ['weight', 'height', 'fat_free_mass', 'fat_ratio', 'fat_mass_weight', 'diastolic_blood_pressure',
                            'systolic_blood_pressure', 'heart_pulse', 'temperature', 'sp02', 'skin_temperature', 'muscle_mass',
                            'hydration', 'pulse_wave_velocity', 'bone_mass', 'pulse_wave_velocity_imt',
                            'heart_rate_variability', 'heart_rate_variability_sdnn', 'heart_rate_variability_rmssd',
                            'heart_rate_variability_pnn50', 'heart_rate_variability_pnn20']
        df = pd.DataFrame()
        if response.status_code == 200:
            data = response.json()
            columns_names = list(data['body']['measuregrps'][0].keys())
            # add elements of other list
            columns_names.extend(meastype_list)
            columns_names.remove('measures')
            df = pd.DataFrame(columns = columns_names)
            for data in data['body']['measuregrps']:
                # create a new row
                row = {}
                # add all the columns of the row
                for column in columns_names:
                    if column in data:
                        row[column] = data[column]
                    else:
                        row[column] = NaN
                # add the measures
                measures = data['measures']
                for measure in measures:
                    # get the meastype
                    meastype = self.get_meastype(measure['type'])
                    # add the value to the row
                    row[meastype] = measure['value']*10**measure['unit']
                # add the row to the dataframe
                df=pd.concat([df, pd.DataFrame(row, index=[0])], ignore_index=True)

            # substitute the timestamp with the date
            df['date'] = df['date'].apply(lambda x: self.get_date_from_timestamp(x))
            df['created'] = df['created'].apply(lambda x: self.get_date_from_timestamp(x))
            df['modified'] = df['modified'].apply(lambda x: self.get_date_from_timestamp(x))
            # substitute category column if the value is 1: REAL otherwise USER OBJECTIVE
            df['category'] = df['category'].apply(lambda x: 'REAL' if x == 1 else 'USER OBJECTIVE')
            # substitute attribute column 0:automatic, 2: manual
            df['attrib'] = df['attrib'].apply(lambda x: 'AUTO' if x == 0 else 'MANUAL')
            # substitute deviceid with device model from self.devices
            df['deviceid'] = df['deviceid'].apply(lambda x: self.get_device_model(x))
        return df



    def get_activity(self,start_date,end_date):
        # Convert datetime.datetime into a string of the form 'YYYY-MM-DD'
        start_date_ymd = start_date.strftime('%Y-%m-%d')
        end_date_ymd = end_date.strftime('%Y-%m-%d')

        url = f'https://wbsapi.withings.net/v2/measure?action=getactivity&' \
              f'startdateymd={start_date_ymd}&' \
              f'enddateymd={end_date_ymd}&' \
              f'access_token={self.api.get_credentials().access_token}'
        response = requests.get(url)
        df = pd.DataFrame()
        if response.status_code == 200:
            data = response.json()
            columns_names = list(data['body']['activities'][0].keys())
            df = pd.DataFrame(data['body']['activities'],columns=columns_names)
            df['modified'] = df['modified'].apply(lambda x: self.get_date_from_timestamp(x))

        return df
    '''
              f'startdate={int(self.get_unix_timestamp(start_date))}&' \
              f'enddate={int(self.get_unix_timestamp(end_date))}&' '''
    def get_intra_activity(self,start_date,end_date):
        url = f'https://wbsapi.withings.net/v2/measure?' \
              f'action=getintradayactivity&' \
              f'data_fields=heart_rate,steps,elevation,calories,distance,stroke,pool_lap,duration,spo2_auto&' \
              f'access_token={self.api.get_credentials().access_token}'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            time= list(data['body']['series'].keys())
            columns_name = ['time','model','model_id','deviceid','heart_rate','steps','elevation','calories','distance','stroke','pool_lap','duration','spo2_auto']
            df = pd.DataFrame(data['body']['series'].values(),columns = columns_name)
            df['time'] = time
            df['time'] = df['time'].apply(lambda x: self.get_date_from_timestamp(int(x)))
    ''' 
    def get_activity(self, start_date, end_date):
        activity_measure = self.measure_get_activity(data_fields=withings_api.GetActivityField,
                                                     offset=0,
                                                     startdateymd=start_date,
                                                     enddateymd=end_date)
        activity_data = activity_measure.activities
        columns = list(activity_data[0].__fields_set__)
        activity_df = self.create_df_from_data(activity_data)
        if path.isfile("ACTIVITY_DATA.csv"):
            os.remove("ACTIVITY_DATA.csv")
        activity_df.to_csv("ACTIVITY_DATA.csv", index=False)

    def get_heart(self, start_date, end_date):
        heart_measure = self.heart_list(startdate=start_date, enddate=end_date)
        heart_columns = list(heart_measure.series[0].__fields_set__)
        heart_columns.append('ecg')
        heart_data = heart_measure.series
        heart_df = pd.DataFrame(heart_measure.series, columns=heart_columns)
        if path.isfile("HEART_DATA.csv"):
            os.remove("HEART_DATA.csv")
        heart_df.to_csv("HEART_DATA.csv", index=False)

    def get_sleep(self):
        sleep_measure = self.request(path="v2/sleep",
                                     params={"action": "getsummary",
                                             "startdateymd": arrow.utcnow().shift(
                                                 days=-arrow.utcnow().date().day + 1).format('YYYY-MM-DD'),
                                             "enddateymd": arrow.utcnow().format("YYYY-MM-DD")})
        sleep_df = pd.DataFrame(sleep_measure['series'])
        sleep_df = pd.concat([sleep_df.drop(['data'], axis=1), sleep_df['data'].apply(pd.Series)], axis=1)
        if path.isfile("SLEEP_DATA.csv"):
            os.remove("SLEEP_DATA.csv")
        sleep_df.to_csv("SLEEP_DATA.csv", index=False)
    '''


