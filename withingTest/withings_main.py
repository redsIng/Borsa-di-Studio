import datetime
from Withings import Withings

# Create an auth object with your Withings credentials (needed for 2FA).
# Secrets should be stored in a secure location and not in your code.

# Developer Account information

client_id = "9694b7164bdb2c898f48d343f4fcfb15eac7827323dc9027a7de73634d82c070"
consumer_secret = "0e969c5b4cdfb0743d952b58c4ff444209e0df5c08b377d89383fefbf5701ebd"
# The callback URI is used to get the authorization code. It redirects all the request to
# withigns API at the end of the 2FA procedure to the localhost:5000. "5000" is the port
# that it was set in the developer dashboard.
callback_uri = "https://localhost:5000"

# datetime year, month,day, hour, minute, second
start_date = datetime.datetime(2023, 1, 1, 0, 0, 0)
end_date = datetime.datetime(2023, 2, 24, 0, 0, 0)


withings = Withings(client_id, consumer_secret, callback_uri)

# Authorize the app to access your data
withings.authorize()

meausure_df = withings.get_measure(start_date, end_date)

meausure_df.to_csv("GET_MEAS.csv")
# # Activity measurements

activity_measure = withings.get_activity(start_date, end_date)

activity_measure.to_csv("GET_ACTIVITY.csv")
# GetIntraActivity
start_date = datetime.datetime(2023, 2, 2, 0, 0, 0)
end_date = datetime.datetime(2023, 2, 3, 0, 0, 0)
intra_activity_measure = withings.get_intra_activity(start_date, end_date)

intra_activity_measure.to_csv("GET_INTRA_ACTIVITY.csv")

start_date = datetime.datetime(2023, 1, 1, 0, 0, 0)
end_date = datetime.datetime(2023, 2, 24, 0, 0, 0)
# HeartList To get Signal ID
heart_measure = withings.get_heart_list(start_date, end_date)

heart_measure.to_csv("GET_HEART_LIST.csv")

signal_id = heart_measure['ecg'][1]['signalid']
# Get ECG High Sampling
ecg_measure = withings.get_ecg_high_sampling(signal_id)

ecg_measure.to_csv("GET_ECG_HIGH_SAMPLING.csv")

# Sleep data captured at high frequency only available for 1 day
start_date = datetime.datetime(2023, 2, 15, 0, 0, 0)
end_date = datetime.datetime(2023, 2, 15, 23, 59, 59)
sleep_high_frequency = withings.get_sleep_high_sampling(start_date, end_date)

sleep_high_frequency.to_csv("GET_SLEEP_HIGH_FREQUENCY.csv")

# Sleep data summary aggregation of high sampling
start_date = datetime.datetime(2023, 1, 1, 0, 0, 0)
end_date = datetime.datetime(2023, 2, 20, 0, 0, 0)

sleep_summary = withings.get_sleep_summary(start_date, end_date)
sleep_summary.to_csv("GET_SLEEP_SUMMARY.csv")


#workout_measure = withings.get_workout_measurements(start_date, end_date)

#workout_measure.to_csv("GET_WORKOUT.csv")

