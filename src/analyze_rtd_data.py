import numpy as np
import pandas as pd
import clean_rtd_data
import scipy.stats as stats
import matplotlib.pyplot as plt
plt.style.use('ggplot')
font = {'weight': 'bold'
       ,'size': 16}
plt.rc('font', **font)

class RTD_analyze(object):

    def __init__(self, rtd_data, route_type='All', route_label='All'):
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
        if (self.route_type == 'All') & (self.route_label == 'All'):
            self.data = rtd_data.df
        elif ~(self.route_type == 'All') & (self.route_label == 'All'):
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

    def plot_null_hypothesis(self, ax, alpha_value, null_percent):
        
        null_dist = stats.binom(n=self.total_stops, p=null_percent)
        x = np.linspace(0, self.total_stops, self.total_stops+1)
        observed_data = self.ontime_stops
        
        ax.plot(x, null_dist.pmf(x), label='$H_O$')
        ax.yaxis.set_major_formatter(plt.FormatStrFormatter('%1.2e'))
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        ax.set_xlim(null_dist.ppf(0.00001), null_dist.ppf(0.99999))
        ax.axvline(null_dist.ppf(alpha_value)
                  ,linestyle='--'
                  ,color='grey'
                  ,label='$\\alpha$ = Type I Error')
        ax.fill_between(x
                        ,null_dist.pmf(x)
                        ,where= x <= observed_data
                        ,alpha=0.25
                        ,label=f"P Value = {null_dist.cdf(observed_data):.3f}")
        ax.legend(loc='best')
        ax.set_xlabel('# of On-Time Vehicles')
        ax.set_title(f"{self.route_type.replace('_', ' ').title()} Routes", fontsize=14)

    def plot_alt_hypothesis(self, ax, alpha_value, null_percent):

        null_dist = stats.binom(n=self.total_stops, p=null_percent)
        alt_dist = stats.binom(n=self.total_stops, p=self.ontime_departure_rate)
        x = np.linspace(0, self.total_stops, self.total_stops+1)
        observed_data = self.ontime_stops

        ax.plot(x, null_dist.pmf(x), label='$H_0$')
        ax.plot(x, alt_dist.pmf(x), label='$H_A$')
        ax.yaxis.set_major_formatter(plt.FormatStrFormatter('%1.2e'))
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        ax.set_xlim(min(alt_dist.ppf(0.00001), null_dist.ppf(0.00001)), max(alt_dist.ppf(0.99999), null_dist.ppf(0.99999)))
        ax.axvline(null_dist.ppf(alpha_value), linestyle='--', color='grey', label='critical value')
        ax.fill_between(x, null_dist.pmf(x)
                       ,where= (x <= null_dist.ppf(alpha_value))
                       ,alpha=0.25
                       ,label='$\\alpha$ = Type I Error')
        ax.fill_between(x, alt_dist.pmf(x)
                       ,where= (x >= null_dist.ppf(alpha_value))
                       ,alpha=0.25
                       ,label='$\\beta$ = Type II Error')
        ax.fill_between(x, alt_dist.pmf(x)
                       ,where= (x < null_dist.ppf(alpha_value))
                       ,alpha=0.25
                       ,color='Green'
                       ,label='Power')
        ax.legend(loc='best')
        ax.set_xlabel(f"# of On-Time Vehicles")
        ax.set_title(f"{self.route_type.replace('_', ' ').title()} Routes", fontsize=14)

if __name__ == '__main__':

    rtd_data = clean_rtd_data.RTD_df(bucket_name='rtd-on-time-departure', file_name='rtd_data.csv')
    rtd_data.clean_my_data()

    all_routes = RTD_analyze(rtd_data)
    all_routes.calculate_ontime_departure()

    light_rail = RTD_analyze(rtd_data, route_type='light_rail')
    light_rail.calculate_ontime_departure()
    
    bus = RTD_analyze(rtd_data, route_type='bus')
    bus.calculate_ontime_departure()
    
    fig, ax = plt.subplots(figsize=(15,10))

    ax.hist(all_routes.data.minutes_since_departure, bins=250)
    ax.set_xlabel('Minutes Before/After Schedule')
    ax.set_title('Histogram of Departure Time Before/After Schedule ')
    plt.xlim((-20,20))
    plt.savefig('images/departure_time_histogram.png')

    # Original Null Hypothesis
    set_figsize = (30,10)

    fig, axs = plt.subplots(1,3,figsize=set_figsize)

    all_routes.plot_null_hypothesis(ax=axs[0], alpha_value=0.01, null_percent=0.86)
    light_rail.plot_null_hypothesis(ax=axs[1], alpha_value=0.01, null_percent=0.90)
    bus.plot_null_hypothesis(ax=axs[2], alpha_value=0.01, null_percent=0.86)
    fig.suptitle(f"Binomial Distribution of Null Hypotheses", fontsize=16)
    plt.savefig(f"images/original_null_hypothesis.png")
    
    # Original Alt Hypothesis
    fig, axs = plt.subplots(1,3,figsize=set_figsize)
    
    all_routes.plot_alt_hypothesis(ax=axs[0], alpha_value=0.01, null_percent=0.86)
    light_rail.plot_alt_hypothesis(ax=axs[1], alpha_value=0.01, null_percent=0.90)
    bus.plot_alt_hypothesis(ax=axs[2], alpha_value=0.01, null_percent=0.86)
    fig.suptitle(f"Binomial Distributions of Null and Alternate Hypotheses", fontsize=16)
    plt.savefig(f"images/original_alt_hypothesis.png")

    # Modified Null Hypothesis
    all_routes_null_p = 0.815
    light_rail_null_p = 0.87
    bus_null_p = 0.815

    fig, axs = plt.subplots(1,3,figsize=set_figsize)
    
    all_routes.plot_null_hypothesis(ax=axs[0], alpha_value=0.01, null_percent=all_routes_null_p)
    light_rail.plot_null_hypothesis(ax=axs[1], alpha_value=0.01, null_percent=light_rail_null_p)
    bus.plot_null_hypothesis(ax=axs[2], alpha_value=0.01, null_percent=bus_null_p)
    fig.suptitle(f"Binomial Distributions of Null Hypotheses", fontsize=16)
    plt.savefig(f"images/modified_null_hypothesis.png")

    # Modified Alt Hypothesis
    fig, axs = plt.subplots(1,3,figsize=set_figsize)
    
    all_routes.plot_alt_hypothesis(ax=axs[0], alpha_value=0.01, null_percent=all_routes_null_p)
    light_rail.plot_alt_hypothesis(ax=axs[1], alpha_value=0.01, null_percent=light_rail_null_p)
    bus.plot_alt_hypothesis(ax=axs[2], alpha_value=0.01, null_percent=bus_null_p)
    fig.suptitle(f"Binomial Distributions of Null and Alternate Hypotheses", fontsize=16)
    plt.savefig(f"images/modified_alt_hypothesis.png")
