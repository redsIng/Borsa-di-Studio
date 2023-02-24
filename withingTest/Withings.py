import datetime
import os
import pickle
from os import path
from typing import cast, Final

import numpy as np
import pandas as pd
import requests
import withings_api
from numpy import NaN
from oauthlib.oauth2 import MissingTokenError
from withings_api import CredentialsType, AuthScope


def get_date_from_timestamp(timestamp):
    if timestamp is not None:
        if isinstance(timestamp, str):
            return datetime.datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(timestamp, int):
            return datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    else:
        return None


def get_unix_timestamp(datetime):
    return int(datetime.timestamp())


def apply_date_conversion(df, column_name):
    df[column_name] = df[column_name].apply(lambda x: get_date_from_timestamp(x))


class Withings(withings_api.WithingsAuth):
    client_id = "YOUR_CLIENT_ID"
    consumer_secret = "consumer_secret"
    callback_uri = "http://localhost:8080"
    access_token = "access_token"
    credential_file = path.abspath(
        path.join(path.dirname(path.abspath(__file__)), "..\.credentials")
    )
    SLEEP_STATES = {0: 'light', 1: 'deep', 2: 'rem'}

    scope = (
        AuthScope.USER_ACTIVITY,
        AuthScope.USER_METRICS,
        AuthScope.USER_INFO,
        AuthScope.USER_SLEEP_EVENTS,
    )
    api = None
    BASE_URL: Final = "https://wbsapi.withings.net"
    NO_DATA: Final = "No data available for this period"
    FORMAT_YYYMMDD: Final = '%Y-%m-%d'
    meastype_dict = {1: 'weight', 4: 'height', 5: 'fat_free_mass', 6: 'fat_ratio', 8: 'fat_mass_weight',
                     9: 'diastolic_blood_pressure', 10: 'systolic_blood_pressure', 11: 'Heart Pulse (bpm)',
                     12: 'temperature', 54: 'sp02', 71: 'skin_temperature', 73: 'body_temperature',
                     76: 'muscle_mass', 77: 'hydration', 88: 'bone_mass', 91: 'pulse_wave_velocity_imt',
                     123: 'VO2 max', 135: 'QRS',
                     136: 'PR ', 137: 'QT ',
                     138: 'Corrected QT',
                     139: 'Atrial fibrillation'}
    params = {
        'measure': {
            'action': 'getmeas',
            'startdate': None,
            'enddate': None,
            'meastype': None
        },
        'measure_v2_activity': {
            'action': 'getactivity',
            'startdateymd': None,
            'enddateymd': None
        },
        'measure_v2_intraday_activity': {
            'action': 'getintradayactivity',
            'startdate': None,
            'enddate': None,
            'data_fields': 'steps,elevation,calories,distance,stroke,pool_lap,duration,heart_rate,spo2_auto'
        },
        'heart_list': {
            'action': 'list',
            'startdate': None,
            'enddate': None
        },
        'heart_get': {
            'action': 'get',
            'signalid': None
        },
        'sleep_get': {
            'action': 'get',
            'startdate': None,
            'enddate': None,
            'data_fields': 'hr,rr,snoring,sdnn_1,rmssd'
        },
        'sleep_getsummary': {
            'action': 'getsummary',
            'startdateymd': None,
            'enddateymd': None,
            'data_fields': 'nb_rem_episodes,sleep_efficiency,sleep_latency,total_sleep_time,total_sleep_time,total_timeinbed,'
                           'wakeup_latency,waso,apnea_hypopnea_index,breathing_disturbances_intensity,'
                           'asleepduration,deepsleepduration,durationtosleep,durationtowakeup,'
                           'hr_average,hr_max,hr_min,lightsleepduration,night_events,out_of_bed_count,'
                           'remsleepduration,rr_average,rr_max,rr_min,sleep_score,snoring,'
                           'snoring,spo2_average,spo2_max,spo2_min,spo2_latency,spo2_duration,'
                           'spo2_desaturation_index,spo2_desaturation_count,spo2_desaturation_duration,'
        }
    }

    def __init__(self, consumer_key, consumer_secret, callback_uri):
        self.devices = None
        self.client_id = consumer_key
        self.consumer = consumer_secret
        self.callback_uri = callback_uri
        super().__init__(client_id=self.client_id,
                         consumer_secret=self.consumer,
                         callback_uri=self.callback_uri,
                         scope=self.scope)

    def authorize(self):
        if os.path.isfile(self.credential_file):
            print(f"Attempting to load credentials from: {self.credential_file}")
            self.api = withings_api.WithingsApi(self.load_credentials(), refresh_cb=self._save_credentials_)
            self.api.refresh_token()
            try:
                self.api.user_get_device()
            except MissingTokenError:
                os.remove(self.credential_file)
                print("Credentials in file are expired. Re-starting auth procedure...")
        else:
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

    def _save_credentials_(self, credentials: CredentialsType) -> None:
        """Save credentials to a file."""
        print(f"Saving credentials to: {self.credential_file}")
        with open(self.credential_file, "wb") as file_handle:
            pickle.dump(credentials, file_handle)

    def load_credentials(self) -> CredentialsType:
        """Load credentials from a file."""
        print(f"Using credentials saved in: {self.credential_file}")
        with open(self.credential_file, "rb") as file_handle:
            return cast(CredentialsType, pickle.load(file_handle))

    def device_options(self):
        devices = self.api.user_get_device().devices
        columns = ['type', 'model', 'battery', 'deviceid', 'timezone']
        values = [[x[1] for x in device] for device in devices]
        self.devices = pd.DataFrame(values, columns=columns)

    # enum by integer 0= LEGGERO, 1= PROFONDO, 2=REM
    def get_sleep_state(self, state):
        return self.SLEEP_STATES.get(state, 'unknown')

    def get_meas_type(self, meastype):
        return self.meastype_dict.get(meastype, None)

    def get_device_model(self, deviceid):
        if deviceid is None:
            return 'Withings'
        device_model = self.devices.loc[self.devices['deviceid'] == deviceid, 'model']
        return device_model.values[0] if not device_model.empty else deviceid

    def make_withings_request(self, endpoint, query_params):
        url = f'https://wbsapi.withings.net/{endpoint}?access_token={self.api.get_credentials().access_token}'
        for key, value in query_params.items():
            url += f'&{key}={value}'
        response = requests.get(url)
        if response.ok:
            data = response.json()
            if 'body' in data and data['body'] != []:
                return data['body']
        return None

    def get_measure(self, start_date, end_date):
        self.params['measure']['startdate'] = get_unix_timestamp(start_date)
        self.params['measure']['enddate'] = get_unix_timestamp(end_date)
        self.params['measure']['meastype'] = ','.join([str(x) for x in self.meastype_dict.keys()])
        data = self.make_withings_request('measure', self.params['measure'])
        columns_names = list(data['measuregrps'][0].keys())
        columns_names.extend(self.meastype_dict.values())
        columns_names.remove('measures')
        df = pd.DataFrame(columns=columns_names)
        for data in data['measuregrps']:
            row = {}
            for column in columns_names:
                row[column] = data.get(column, NaN)
            for measure in data['measures']:
                meastype = self.get_meas_type(measure['type'])
                row[meastype] = measure['value'] * 10 ** measure['unit']
            df = pd.concat([df, pd.DataFrame(row, index=[0])], ignore_index=True)
        apply_date_conversion(df, 'date')
        apply_date_conversion(df, 'modified')
        apply_date_conversion(df, 'created')
        df['category'] = df['category'].map({1: 'REAL', 0: 'USER OBJECTIVE'})
        df['attrib'] = df['attrib'].map({0: 'AUTO', 2: 'MANUAL'})
        df['deviceid'] = df['deviceid'].apply(lambda x: self.get_device_model(x))
        return df

    def get_activity(self, start_date, end_date):
        self.params['measure_v2_activity']['startdateymd'] = start_date.strftime(self.FORMAT_YYYMMDD)
        self.params['measure_v2_activity']['enddateymd'] = end_date.strftime(self.FORMAT_YYYMMDD)
        data = self.make_withings_request('v2/measure', self.params['measure_v2_activity'])
        columns_names = list(data['activities'][0].keys())
        df = pd.DataFrame(data['activities'], columns=columns_names)
        apply_date_conversion(df, 'modified')
        return df

    def get_intra_activity(self, start_date, end_date):
        self.params['measure_v2_intraday_activity']['startdate'] = get_unix_timestamp(start_date)
        self.params['measure_v2_intraday_activity']['enddate'] = get_unix_timestamp(end_date)
        data = self.make_withings_request('v2/measure', self.params['measure_v2_intraday_activity'])
        time = list(data['series'].keys())
        columns_name = ['time', 'model', 'model_id', 'deviceid', 'heart_rate', 'steps', 'elevation', 'calories',
                        'distance', 'stroke', 'pool_lap', 'duration', 'spo2_auto']
        df = pd.DataFrame(data['series'].values(), columns=columns_name)
        df['time'] = time
        apply_date_conversion(df, 'time')
        return df

    def get_workout_measurements(self, start_date, end_date):
        start_date_ymd = start_date.strftime(self.FORMAT_YYYMMDD)
        end_date_ymd = end_date.strftime(self.FORMAT_YYYMMDD)
        url = f'https://wbsapi.withings.net/v2/measure?action=getworkouts&' \
              f'startdateymd={start_date_ymd}&' \
              f'enddateymd={end_date_ymd}&' \
              f'data_fields=calories,intensity,manual_distance,manual_calories,hr_average,hr_min,hr_max,' \
              f'hr_zone_0,hr_zone_1,hr_zone_2,hr_zone_3,pause_duration,algo_pause_duration,spo2_average' \
              f'steps,distance,elevation,pool_laps,strokes,pool_length' \
              f'access_token={self.api.get_credentials().access_token}'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['body']['workouts'] != []:
                columns_names = list(data['body']['workouts'][0].keys())
                df = pd.DataFrame(data['body']['workouts'], columns=columns_names)
                df['modified'] = df['modified'].apply(lambda x: get_date_from_timestamp(x))
                return df
            else:
                print(self.NO_DATA)
                return None

    def get_heart_list(self, start_date, end_date):
        self.params['heart_list']['startdate'] = get_unix_timestamp(start_date)
        self.params['heart_list']['enddate'] = get_unix_timestamp(end_date)
        data = self.make_withings_request('v2/heart', self.params['heart_list'])
        columns_names = list(data['series'][0].keys())
        df = pd.DataFrame(data['series'], columns=columns_names)
        apply_date_conversion(df, 'modified')
        apply_date_conversion(df, 'timestamp')
        df['deviceid'] = df['deviceid'].apply(lambda x: self.get_device_model(x))
        return df

    def get_ecg_high_sampling(self, signal_int):
        self.params['heart_get']['signalid'] = signal_int
        data = self.make_withings_request('v2/heart', self.params['heart_get'])
        df = pd.DataFrame(columns=['sampling_frequency', 'wearposition', 'model', 'grpid', 'value', 'date', 'signal'])
        for i in range(len(data['signal'])):
            df.loc[i] = [data['sampling_frequency'],
                         data['wearposition'],
                         data['model'],
                         data['heart_rate']['grpid'],
                         data['heart_rate']['value'],
                         data['heart_rate']['date'],
                         data['signal'][i]]
        apply_date_conversion(df, 'date')

        return df

    def get_sleep_high_sampling(self, start_date, end_date):
        self.params['sleep_get']['startdate'] = get_unix_timestamp(start_date)
        self.params['sleep_get']['enddate'] = get_unix_timestamp(end_date)

        data = self.make_withings_request('v2/sleep', self.params['sleep_get'])

        columns_names = list(data['series'][0].keys())
        columns_names.extend(['hr', 'rr', 'snoring', 'sdnn_1', 'rmssd'])
        df = pd.DataFrame(data['series'], columns=columns_names)
        for i in range(len(df['hr'])):
            if isinstance(df['hr'][i], dict):
                hr_dict = {str(get_date_from_timestamp(int(key))): value for key, value in
                           df['hr'].iloc[i].items()}
                df.at[i, 'hr'] = hr_dict  # change df['state'] according to the values
        df['state'] = df['state'].apply(lambda x: self.get_sleep_state(x))
        apply_date_conversion(df, 'startdate')
        apply_date_conversion(df, 'enddate')
        return df

    def get_sleep_summary(self, start_date, end_date):
        self.params['sleep_getsummary']['startdateymd'] = start_date.strftime(self.FORMAT_YYYMMDD)
        self.params['sleep_getsummary']['enddateymd'] = end_date.strftime(self.FORMAT_YYYMMDD)
        data = self.make_withings_request('v2/sleep', self.params['sleep_getsummary'])
        columns_names = list(data['series'][0].keys())
        df = pd.DataFrame(data['series'], columns=columns_names)
        df = df.join(pd.DataFrame(df['data'].tolist()))
        df.drop('data', axis=1, inplace=True)
        apply_date_conversion(df, 'startdate')
        apply_date_conversion(df, 'enddate')
        apply_date_conversion(df, 'created')
        apply_date_conversion(df, 'modified')

        return df
