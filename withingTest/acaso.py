# Activity measurements
tiactivity_measure = api.measure_get_activity(data_fields=GetActivityField,
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
# sleep_measure['series'][0]['data'] expend the value as columns of dataset
sleep_df = pd.concat([sleep_df.drop(['data'], axis=1), sleep_df['data'].apply(pd.Series)], axis=1)
if path.isfile("SLEEP_DATA.csv"):
    os.remove("SLEEP_DATA.csv")
sleep_df.to_csv("SLEEP_DATA.csv", index=False)
