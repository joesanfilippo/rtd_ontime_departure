import numpy as np
import pandas as pd
import geopy.distance as geo
import matplotlib.pyplot as plt
import re

class RTD_df(object):

    def __init__(self, df):
        '''
        Initialize instance of a DataFrame with RTD info:

        Args: 
            df (pd.DataFrame): A pandas DataFrame with RTD info in it.
        '''
        self.df = df

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
            self.df[column] = pd.to_datetime(self.df[column], unit='s').dt.tz_localize(current_timezone).dt.tz_convert(local_timezone)

    def parse_codes(self, colname, code_dict):
        '''
        Converts coded integers to their real-world values given in the code_dict

        Args:
            colname (str): column name of dataframe that contains the coded values to be converted

            code_dict (dict): dictionary of code conversion where the keys are the code integers and values 
            are their corresponding real-world values.
        '''
        self.df[colname] = self.df[colname].replace(to_replace = code_dict)

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

    def calculate_time(self, time_1, time_2, new_column):
        '''
        Calculates the time in minutes between a timestamp and a string in the format %H:%M:%S

        Args:
            time_1 (str): The name of the column with timestamp values to use for the first time

            time_2 (str): The name of the column with string values in the format %H:%M:%S to use for the second time

            new_column (str): The name of the new column created from the difference in times
        '''
        time_diff = pd.to_datetime(self.df[time_1]).dt.tz_localize(None) - self.df[time_2].apply(lambda x: pd.Timestamp(x))
        self.df[new_column] = round(time_diff.apply(lambda x: x.total_seconds()/60), 2)

if __name__ == '__main__':

    rtd_data = RTD_df(pd.read_csv('~/Documents/dsi/repos/rtd_on_time_departure/data/rtd_data.csv'))
    
    rtd_data.join_txt_file('~/Documents/dsi/repos/rtd_on_time_departure/data/google_transit/routes.txt', 'left', ['route_id'])
    rtd_data.join_txt_file('~/Documents/dsi/repos/rtd_on_time_departure/data/google_transit/trips.txt', 'left', ['trip_id'])
    rtd_data.join_txt_file('~/Documents/dsi/repos/rtd_on_time_departure/data/google_transit/stops.txt', 'left', ['stop_id'])
    rtd_data.join_txt_file('~/Documents/dsi/repos/rtd_on_time_departure/data/google_transit/stop_times.txt', 'left', ['trip_id', 'stop_id'])

    rtd_data.df = rtd_data.df[(~rtd_data.df.stop_name.isnull()) & (~rtd_data.df.departure_time.isnull())]

    rtd_data.df = rtd_data.df.loc[:,['entity_id'
                  ,'trip_id'
                  ,'trip_headsign'
                  ,'route_id'
                  ,'route_long_name'
                  ,'route_short_name'
                  ,'route_type'
                  ,'route_desc'
                  ,'vehicle_lat'
                  ,'vehicle_lng'
                  ,'bearing'
                  ,'current_status'
                  ,'timestamp'
                  ,'stop_id'
                  ,'stop_name'
                  ,'stop_desc'
                  ,'stop_lat'
                  ,'stop_lon'
                  ,'arrival_time'
                  ,'departure_time'
                  ,'vehicle_id'
                  ,'vehicle_label']]

    status_dict = {0: 'incoming_at'
                  ,1: 'stopped_at'
                  ,2: 'in_transit_to'}

    route_dict = {0: 'light_rail'
                 ,2: 'commuter_rail'
                 ,3: 'bus'}

    rtd_data.parse_codes('current_status', status_dict)
    rtd_data.parse_codes('route_type', route_dict)
    rtd_data.convert_timezone_local(['timestamp'], 'UTC', 'US/Mountain')
    rtd_data.calculate_distance('vehicle_lat', 'vehicle_lng', 'stop_lat', 'stop_lon', 'meters_from_stop')

    rtd_data.df = rtd_data.df.replace({'arrival_time': r'^24', 'departure_time': r'^24'}, '00', regex=True)
    rtd_data.df = rtd_data.df.replace({'arrival_time': r'^25', 'departure_time': r'^25'}, '00', regex=True)
    rtd_data.calculate_time('timestamp', 'departure_time', 'minutes_from_stop')

    print(rtd_data.df.info()) 
    total_stops = rtd_data.df.groupby(['route_id', 'stop_name']).trip_id.nunique().reset_index()
    unique_stops = total_stops.trip_id.sum()

    print(f'Number of unique stops collected: {unique_stops}')