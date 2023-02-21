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
start_date = datetime.datetime(2023, 2, 1, 0, 0, 0)
end_date = datetime.datetime(2023, 2, 20, 0, 0, 0)


withings = Withings(client_id, consumer_secret, callback_uri)
print("Withings object created")

# Authorize the app to access your data
withings.authorize()

meausure_df = withings.get_measure(start_date, end_date)

print("CIAO")

# # Activity measurements

activity_measure = withings.get_activity(start_date, end_date)

# GetIntraActivity

intra_activity_measure = withings.get_intra_activity(start_date, end_date)