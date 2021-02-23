import re
import os
import io
import boto3
import numpy as np
import pandas as pd
import geopy.distance as geo

class RTD_df(object):

    def __init__(self, bucket_name, file_name):
        '''
        Initialize instance of a RTD_df class with the AWS bucket and filename:

        Args: 
            bucket_name (string): The name of an AWS bucket with the csv datafile in it.
            file_name (string): A csv filename where the RTD data is stored.
        '''
        self.bucket_name = bucket_name
        self.file_name = file_name

        aws_id = os.environ['AWS_ACCESS_KEY_ID']
        aws_secret = os.environ['AWS_SECRET_ACCESS_KEY']
        client = boto3.client('s3'
                             ,aws_access_key_id=aws_id
                             ,aws_secret_access_key=aws_secret)

        csv_obj = client.get_object(Bucket=self.bucket_name, Key=self.file_name)
        self.df = pd.read_csv(io.BytesIO(csv_obj['Body'].read()), encoding='utf8')
        
    def convert_timezone_local(self, colname_list, current_timezone, local_timezone): 
        '''
        Converts the columns in colname_list to local timezone

        Args:
            colname_list (list): list of column names (strings) to convert in the RTD_df.df class. 
                                Values should be int for conversion
            current_timezone (str): string of timezone that the column name currently is in
            local_timezone (str): string of the timezone that the column name should be converted to.
        '''
        for column in colname_list:
            self.df.loc[:, column] = pd.to_datetime(self.df[column], unit='s').dt.tz_localize(current_timezone).dt.tz_convert(local_timezone)

    def shift_departures(self, sorted_columns, grouped_columns, shifted_columns, new_column_names):
        '''
        Shift columns by -1 to account for departure data

        Args:
            sorted_columns (list): list of column names (strings) to sort the dataframe by first
            grouped_columns (list): list of column names (strings) to group the dataframe by for shifting
            shifted_columns (list): list of column names (strings) to shift by -1
            new_column_names: list of column names (strings) to call the new shifted columns, should have 
                same len() as shifted_columns
        '''
        try:
            len(shifted_columns) == len(new_column_names)
            self.df = self.df.sort_values(sorted_columns)
            for new_col, shift_col in zip(new_column_names, shifted_columns):
                self.df.loc[:, new_col] = self.df.groupby(grouped_columns)[shift_col].shift(-1)
        except:
            print('Shifted Columns and New Column Names must have the same length')

    def join_txt_file(self, txt_file, join_type, join_columns):
        '''
        Joins a txt column to a pandas DataFrame by the join_column(s) using the type of join passed ('left', 'outer')
        
        Args:
            txt_file (str): Filepath to a text file that is separated by ','

            join_type (str): The type of join to use (Left, Outer, Inner, Full)

            join_columns (list): The columns to perform the join with
        '''
        try: 
            self.df = pd.merge(self.df, pd.read_csv(txt_file, delimiter=','), how=join_type, on=join_columns, suffixes=('', '_joined')) 
        except:
            print(f'Failed joining on {join_columns}')
            print(f'Current Columns: {self.df.columns}')
            print(f"Joined Columns: {pd.read_csv(txt_file, delimiter=',').columns}")
    
    def parse_codes(self, colname, code_dict):
        '''
        Converts coded integers to their real-world values given in the code_dict

        Args:
            colname (str): column name of dataframe that contains the coded values to be converted

            code_dict (dict): dictionary of code conversion where the keys are the code integers and values 
            are their corresponding real-world values.
        '''
        self.df[colname] = self.df[colname].replace(to_replace = code_dict)

    def calculate_time(self, time_1, time_2, new_column):
        '''
        Calculates the time in minutes between a timestamp and a string in the format %H:%M:%S

        Args:
            time_1 (str): The name of the column with timestamp values to use for the first time

            time_2 (str): The name of the column with string values in the format %H:%M:%S to use for the second time

            new_column (str): The name of the new column created from the difference in times
        '''
        p = re.compile('00:\d{2}')
        overnight = ((self.df[time_2].apply(lambda x: bool(p.match(x[0:5])))) & (self.df[time_1].apply(lambda x: x.hour) == 23))
        self.df.loc[~overnight, 'day_date'] = (self.df[time_1].dt.to_period('D')).astype(str)
        self.df.loc[overnight, 'day_date'] = (self.df[time_1].dt.to_period('D') + np.timedelta64(1,'D')).astype(str)
        scheduled_timestamp = pd.to_datetime(self.df.day_date + ' ' + self.df[time_2])
        time_diff = self.df[time_1].dt.tz_localize(None) - scheduled_timestamp.apply(lambda x: pd.Timestamp(x))
        self.df[new_column] = time_diff.apply(lambda x: x.total_seconds()/60)

    def calculate_distance(self, point_1_lat, point_1_lng, point_2_lat, point_2_lng, new_column):
        '''
        Calculates the distance between two points in meters given their lat/lng

        Args: 
            point_1_lat (str): The name of the column with the first points latitudes

            point_1_lng (str): The name of the column with the first points longitudes

            point_2_lat (str): The name of the column with the second points latitudes

            point_2_lng (str): The name of the column with the second points longitudes

            new_column (str): The name of the new column created from the lat/lng points
        '''
        point_1 = list(zip(self.df[point_1_lat], self.df[point_1_lng]))
        point_2 = list(zip(self.df[point_2_lat], self.df[point_2_lng]))
        
        self.df[new_column] = [round(geo.distance(point_1, point_2).m,2) if (~pd.isnull(point_2[0])) & (point_1[0] > 0) else np.nan for point_1, point_2 in zip(point_1, point_2)]

    def clean_my_data(self):
        # Remove any NaNs from the timestamp field
        self.df = self.df[(~self.df.timestamp.isnull())]

        # Convert the timezone to local time
        self.convert_timezone_local(['timestamp'], 'UTC', 'US/Mountain')
        
        # Shift the time, lat/lng, and stop columns to get departure data 
        self.shift_departures(sorted_columns = ['vehicle_id', 'timestamp']
                        ,grouped_columns = ['trip_id', 'vehicle_label']
                        ,shifted_columns = ['timestamp', 'vehicle_lat', 'vehicle_lng', 'stop_id']
                        ,new_column_names = ['departure_timestamp', 'departure_vehicle_lat', 'departure_vehicle_lng', 'next_stop_id'])

        # Remove NaNs from stop_id and any rows where arrival stop == departure stop (meaning we are not at 
        # stop yet, but in transit to a stop)
        self.df = self.df[~(self.df.stop_id == self.df.next_stop_id)]
        self.df = self.df[~self.df.next_stop_id.isnull()]

        # Join the GTFS files for routes, trips, stops, and stop times
        self.join_txt_file('~/Documents/dsi/repos/rtd_ontime_departure/data/google_transit/routes.txt', 'left', ['route_id'])
        self.join_txt_file('~/Documents/dsi/repos/rtd_ontime_departure/data/google_transit/trips.txt', 'left', ['trip_id'])
        self.join_txt_file('~/Documents/dsi/repos/rtd_ontime_departure/data/google_transit/stops.txt', 'left', ['stop_id'])
        self.join_txt_file('~/Documents/dsi/repos/rtd_ontime_departure/data/google_transit/stop_times.txt', 'left', ['trip_id', 'stop_id'])

        # Remove NaNs from stop names because the stop.txt file is not 100% up to date
        # Remove any vehicle lat that <= 0.0 and any vehicle lng that is >= -104.8 (outside of RTD's service area)
        self.df = self.df[~(self.df.stop_name.isnull()) & (self.df.vehicle_lat > 0.0) & (self.df.vehicle_lng < -104.8)]

        # Select just the column names we want to use going forward.
        self.df = self.df.loc[:,['entity_id'
                    ,'vehicle_id'
                    ,'vehicle_label'
                    ,'trip_id'
                    ,'trip_headsign'
                    ,'route_id'
                    ,'route_type'
                    ,'route_long_name'
                    ,'route_short_name'
                    ,'route_desc'
                    ,'current_status'
                    ,'stop_id'
                    ,'stop_name'
                    ,'stop_desc'
                    ,'vehicle_lat'
                    ,'vehicle_lng'
                    ,'stop_lat'
                    ,'stop_lon'
                    ,'departure_vehicle_lat'
                    ,'departure_vehicle_lng'
                    ,'timestamp'
                    ,'arrival_time'
                    ,'departure_timestamp'
                    ,'departure_time']]

        # Convert the current_status and route_type values to their real-world counterparts
        status_dict = {0: 'incoming_at'
                    ,1: 'stopped_at'
                    ,2: 'in_transit_to'}
        route_dict = {0: 'light_rail'
                    ,2: 'commuter_rail'
                    ,3: 'bus'}
        self.parse_codes('current_status', status_dict)
        self.parse_codes('route_type', route_dict)

        # Rename the arrival columns to help differentiate them from departure columns
        self.df.rename({'timestamp': 'arrival_timestamp'
                ,'arrival_time': 'scheduled_arrival_time'
                ,'departure_time': 'scheduled_departure_time'
                ,'vehicle_lat': 'arrival_vehicle_lat'
                ,'vehicle_lng': 'arrival_vehicle_lng'
                ,'stop_lon': 'stop_lng'}, axis=1, inplace=True)
        
        # Remove any NaNs from departure times, or scheduled arrival/departure times
        self.df = self.df[(~self.df.departure_timestamp.isnull())
                        & (~self.df.scheduled_arrival_time.isnull()) 
                        & (~self.df.scheduled_departure_time.isnull())
                    ]

        # Fix errors in stop_times.txt where the scheduled arrival or departure time could have 24 or 25 in the hour spot
        self.df = self.df.replace({'scheduled_arrival_time': {r'^24':'00'
                                                             ,r'^25':'00'}
                                  ,'scheduled_departure_time': {r'^24':'00'
                                                               ,r'^25':'00'}
                                  }, regex=True)

        # Calcuate the time between the arrival/departure timestamp and when the scheduled arrival/departure time was supposed to be
        self.calculate_time('arrival_timestamp', 'scheduled_arrival_time', 'minutes_to_arrival')
        self.calculate_time('departure_timestamp', 'scheduled_departure_time', 'minutes_since_departure')

        # Calculate the distance between the arrival/departure location and where the scheduled stop is located
        self.calculate_distance('arrival_vehicle_lat', 'arrival_vehicle_lng', 'stop_lat', 'stop_lng', 'meters_to_arrival')
        self.calculate_distance('departure_vehicle_lat', 'departure_vehicle_lng', 'stop_lat', 'stop_lng', 'meters_since_departure')

if __name__ == '__main__':

    # Instantiate the RTD_df class
    rtd_data = RTD_df(bucket_name='rtd-on-time-departure', file_name='rtd_data.csv')
    
    rtd_data.clean_my_data()

    print(rtd_data.df.shape)