#!/opt/anaconda3/bin/python3

# Documentation: https://developers.google.com/transit/gtfs-realtime
from google.transit import gtfs_realtime_pb2
import requests
import pandas as pd

class RTD_Feed(object):

    def __init__(self, url):
        '''
        Creates a class of RTD Feed that pulls in the data from the protocol buffer file.
        
        Args:
            URL (str): url of the GTFS feed that points to the protocol buffer file.
            e.g. RTD Vehicle Position feed: 'https://www.rtd-denver.com/files/gtfs-rt/VehiclePosition.pb'
        '''
        self.feed = gtfs_realtime_pb2.FeedMessage()
        self.response = requests.get(url)
        self.feed.ParseFromString(self.response.content)
    
    def parse_to_df(self):
        '''
        Parses the feed from the protocol buffer and pulls the values passed in from dict_of_values

        Args:
            dict_of_values (dict): A dictionary where the key is a string that will refer to the 
            column name in the passed dataframe and the value is the entity.vehicle.trip | position 
            | current_status | timestamp | stop | vehicle info.

        Returns:
            pandas DataFrame (pd.DataFrame): where the column titles are the keys from dict_of_values 
            and the values are the values for each entity pulled from the feed.
        '''
        vehicle_dict = {}

        for entity in self.feed.entity:
            if (entity.HasField('id')) & (entity.vehicle.HasField('trip')):
                vehicle_dict[entity.id] = {}
                vehicle_dict[entity.id]['trip_id'] = entity.vehicle.trip.trip_id
                vehicle_dict[entity.id]['schedule_relationship'] = entity.vehicle.trip.schedule_relationship
                vehicle_dict[entity.id]['route_id'] = entity.vehicle.trip.route_id
                vehicle_dict[entity.id]['direction_id'] = entity.vehicle.trip.direction_id
                vehicle_dict[entity.id]['vehicle_lat'] = entity.vehicle.position.latitude
                vehicle_dict[entity.id]['vehicle_lng'] = entity.vehicle.position.longitude
                vehicle_dict[entity.id]['bearing'] = round(entity.vehicle.position.bearing)
                vehicle_dict[entity.id]['current_status'] = entity.vehicle.current_status
                vehicle_dict[entity.id]['timestamp'] = entity.vehicle.timestamp
                vehicle_dict[entity.id]['stop_id'] = entity.vehicle.stop_id
                vehicle_dict[entity.id]['vehicle_id'] = entity.vehicle.vehicle.id
                vehicle_dict[entity.id]['vehicle_label'] = entity.vehicle.vehicle.label
        
        # Debugging
        # for k,v in vehicle_dict.items():
        #     print(f'{k}: {v}')
    
        return pd.DataFrame.from_dict(vehicle_dict, orient='index').rename_axis('entity_id').reset_index()

if __name__ == '__main__':
    
    vehicle_position_url = 'https://www.rtd-denver.com/files/gtfs-rt/VehiclePosition.pb'

    rtd_feed = RTD_Feed(vehicle_position_url)
    rtd_df = rtd_feed.parse_to_df()

    filepath = '~/Documents/dsi/repos/rtd_on_time_departure/data/rtd_data.csv'
    init_csv = pd.DataFrame([['']*len(rtd_df.columns)], columns = rtd_df.columns.tolist()).reset_index(drop=True)
    init_csv.to_csv(filepath, index=False)

# Crontab
# 0 0 10 2 * cd ~/Documents/dsi/repos/rtd_on_time_departure/src && /opt/anaconda3/bin/python3 rtd_feed.py >> ~/Documents/dsi/repos/rtd_on_time_departure/cron_files/init_cron.rtf 2>&1