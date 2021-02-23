import numpy as np
import pandas as pd
import clean_rtd_data
import matplotlib.pyplot as plt
plt.style.use('ggplot')
font = {'weight': 'bold','size':   16}
plt.rc('font', **font)

class RTD_analyze(object):

    def __init__(self, rtd_data, route_type='ALL', route_label='ALL'):
        '''
        Initialize instance of RTD_analyze class that will be used to calculate on-time arrival rate

        Args: 
            rtd_data (RTD_df): The cleaned RTD_df class to analyze
            route_type (string): The different route types to analyze. Can be 'bus' or 'light_rail'.
            route_label (string): The specific route to analyze within a route_type. 
                                 If left blank, all routes will be analyzed and aggregated.
        '''
        self.route_type = route_type
        self.route_label = route_label
        if (self.route_type == 'ALL') & (self.route_label == 'ALL'):
            self.data = rtd_data.df
        elif ~(self.route_type == 'ALL') & (self.route_label == 'ALL'):
            self.data = rtd_data.df[rtd_data.df.route_type == self.route_type]
        else:
            self.data = rtd_data.df[rtd_data.df.route_label == self.route_label]

    def calculate_ontime_departure(self):
        '''
        Calculate the # of times in the RTD_analyze.data that a vehicle was on_time vs not.
        '''
        self.ontime_departure = []
    
        for rt, dt in zip(self.data.route_type, self.data.minutes_since_departure):
            if ((rt == 'bus') | (rt == 'light_rail')) & (dt >= -1) & (dt <= 5):
                self.ontime_departure.append('on_time')
            elif (rt == 'commuter_rail') & (dt >= 0) & (dt <= 5):
                self.ontime_departure.append('on_time')
            elif ((rt == 'bus') | (rt == 'light_rail')) & (dt < -1):
                self.ontime_departure.append('early')
            elif (rt == 'commuter_rail') & (dt < 0):
                self.ontime_departure.append('early')
            elif ((rt == 'bus') | (rt == 'light_rail')) & (dt > 5):
                self.ontime_departure.append('late')
            elif (rt == 'commuter_rail') & (dt > 5):
                self.ontime_departure.append('late')
        self.data.loc[:, 'departure_status'] = self.ontime_departure
        self.total_stops = self.data.shape[0]
        self.ontime_stops = sum(self.data.departure_status == 'on_time')
        self.ontime_departure_rate = self.ontime_stops / self.total_stops

if __name__ == '__main__':

    rtd_data = clean_rtd_data.RTD_df(bucket_name='rtd-on-time-departure', file_name='rtd_data.csv')
    rtd_data.clean_my_data()

    all_routes = RTD_analyze(rtd_data)
    all_routes.calculate_ontime_departure()

    light_rail = RTD_analyze(rtd_data, route_type='light_rail')
    light_rail.calculate_ontime_departure()
    
    bus = RTD_analyze(rtd_data, route_type='bus')
    bus.calculate_ontime_departure()
    
    # try:
    fig, ax = plt.subplots(figsize=(10,5))

    ax.hist(all_routes.data.minutes_since_departure, bins=250)
    ax.set_xlabel('Minutes Before/After Schedule')
    _ = ax.set_title('Histogram of Departure Time Before/After Schedule ')
    # _ = plt.xlim((-20,20))
    
    plt.savefig('../images/departure_time_histogram.png')
    print('Figure Saved!')
    # except:
        # print('Something went wrong...')