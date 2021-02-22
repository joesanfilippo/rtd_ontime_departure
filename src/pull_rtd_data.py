#!/opt/anaconda3/bin/python3

from rtd_feed import RTD_Feed
import pandas as pd
from datetime import datetime

if __name__ == '__main__':

    vehicle_position_url = 'https://www.rtd-denver.com/files/gtfs-rt/VehiclePosition.pb'

    rtd_feed_data = RTD_Feed(vehicle_position_url)
    rtd_df = rtd_feed_data.parse_to_df()

    filepath = '~/Documents/dsi/repos/rtd_on_time_departure/data/rtd_data.csv'
    today_date = datetime.today()
    update_string = today_date.strftime('%Y-%m-%d %H:%M:%S')

    try:
        rtd_df.to_csv(filepath, mode='a', header=False, index=False)
        print(f"Feed Updated at: {update_string}. {rtd_df.shape[0]} rows added.")
    except:
        print('Somthing went wrong...')   
    
# Crontab
# */2 * 10-22 2 * cd ~/Documents/dsi/repos/rtd_on_time_departure/src && /opt/anaconda3/bin/python3 pull_rtd_data.py >> ~/Documents/dsi/repos/rtd_on_time_departure/cron_files/pull_cron.rtf 2>&1