import requests
import pandas as pd
import numpy as np

import yfinance as yf

import matplotlib.pyplot as plt

from mv_avg_window_optimizer import Optimized_Symbol

from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
pio.renderers.default = "browser"

# NLP stuff
# import sklearn
import nltk, re, sqlite3
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from collections import Counter

from bs4 import BeautifulSoup

from datetime import datetime

def get_db_connection():
    conn = sqlite3.connect('./db/database.db')
    conn.row_factory = sqlite3.Row
    return conn

class StockData:
    def __init__(self):
        # get the biggest gainers for the day
        self.gainers_df = self.get_biggest_gainers()
        # build history of the stocks in the gainers (build_stocks_df)
        self.history_df = self.build_stocks_df(self.gainers_df)
        self.ma_df = self.n_day_moving_average()
        self.bol_df = self.bolinger_bands('optimum_day_moving_average', 20)
        self.db_conn = get_db_connection()
        
        
    def get_optimized_ma_params(self) -> pd.DataFrame:
        """
        Fetches optimize parameters or updates parameters for all symbols in object
        """
        for symbol in self.history_df['Symbol'].unique():  
            conn = get_db_connection()  
            # find single and mult day optimum moving averages
            ## First, check if symbol is in db
            opt_params_df = pd.read_sql_query(f"""SELECT MAX(datetime), opt_single_ma_window, opt_two_ma_window_1, opt_two_ma_window_2
                FROM symbol_param_optimized
                WHERE symbol = '{symbol}';""",
                con=conn)
            if opt_params_df.iloc[0,0] == None:
                # calculate optimum params and write to db
                self.calc_optimum_params()
                opt_params_df = pd.read_sql_query(f"""SELECT MAX(datetime), opt_single_ma_window, opt_two_ma_window_1, opt_two_ma_window_2
                    FROM symbol_param_optimized
                    WHERE symbol = '{symbol}';""",
                    con=conn)
        
        
    def update_params_db(self):
        """
        For those symbols that did not exist in the database when checked from get_optimized_ma_params(), updates the database with their information
        """
        pass
                
                                        
    def calc_optimum_params(self, symbol):
        single_opts = Optimized_Symbol.Single_Parameter_Optimizer(self.history_df)
        two_opts = Optimized_Symbol.Multiple_Parameter_Optimizer(self.history_df)
        payload = pd.DataFrame({'symbol':symbol,
                'datetime':datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
                'opt_single_ma_window':single_opts.optimum_window,
                'opt_single_multiple':single_opts.optimum_multiple,
                'opt_two_ma_window_1':two_opts.optimum_window_1,
                'opt_two_ma_window_2':two_opts.optimum_window_2,
                'opt_two_multiple':two_opts.optimum_multiple,
                'organic_growth':single_opts.organic_growth},
                index=[0])
        payload.to_sql('symbol_param_optimized',
                con=self.db_conn,
                if_exists='append',
                index=False)
    
    def get_biggest_gainers(self) -> pd.DataFrame:
        r = requests.get('https://www.dogsofthedow.com/biggest-stock-gainers-today.htm')
        gainers_df = pd.read_html(r.text)[0]
        return gainers_df

    def get_history(self, ticker, period) -> pd.DataFrame:
        t = yf.Ticker(ticker)
        return t.history(period)

    def build_stocks_df(self, gainers_df) -> pd.DataFrame:
        loop = 0
        period = "12mo"
        for s in gainers_df['Symbol']:
            if loop == 0:
                df = self.get_history(s, period=period)
                df['Symbol'] = s
                loop +=1
            else:
                temp_df = self.get_history(s, period=period)
                temp_df['Symbol'] = s
                df = pd.concat([df, temp_df])  
        return df
    
    def n_day_moving_average(self, rolling_window=20):
        """
        Calculates and creates twenty day moving average values into the dataframe
        """
        # reset the index to an array
        df = self.history_df.copy()
        df.reset_index(inplace=True)
        for symbol in df['Symbol'].unique():
            # get min and max index references to pass to .loc later
            idx_ref_min = min(df[df['Symbol']==symbol].index)
            idx_ref_max = max(df[df['Symbol']==symbol].index)
            
            close_series = df[df['Symbol']==symbol]['Close']
            rolling = close_series.rolling(window=rolling_window)
            twenty_day_rolling = rolling.mean()
            
            # set twenty day rolling average at proper indexes for given symbol
            df.loc[idx_ref_min:idx_ref_max+1,f'optimum_day_moving_average'] = twenty_day_rolling
            
        df.set_index('Date', inplace=True)
        return df
    
    def bolinger_bands(self, rolling_avg_col, rolling_window):
        """
        Calculates and creates bolinger band values (upper and lower) into the dataframe
        """
        # reset the index to an array
        df = self.ma_df
        df.reset_index(inplace=True)
        for symbol in df['Symbol'].unique():
            # get min and max index references to pass to .loc later
            idx_ref_min = min(df[df['Symbol']==symbol].index)
            idx_ref_max = max(df[df['Symbol']==symbol].index)
            
            n_day_rolling = df[df['Symbol']==symbol][rolling_avg_col].rolling(window=rolling_window)
            standard_dev = n_day_rolling.std()
            
            # set twenty day rolling average at proper indexes for given symbol
            df.loc[idx_ref_min:idx_ref_max+1,'bolinger_upper_band'] = df.loc[idx_ref_min:idx_ref_max+1,rolling_avg_col] + standard_dev*2
            df.loc[idx_ref_min:idx_ref_max+1,'bolinger_lower_band'] = df.loc[idx_ref_min:idx_ref_max+1,rolling_avg_col] - standard_dev*2
            
        df.set_index('Date', inplace=True)

        return df       


def graph_trend(df, symbol):
    x=np.array([n for n in range(0,len(df[df['Symbol']==symbol]))])
    y=np.array(df[df['Symbol']==symbol]['Close'])
    a, b = np.polyfit(x, y, 1)
    df[df['Symbol']==symbol]['Close'].plot()
    plt.plot(df[df['Symbol']==symbol]['Close'].index, a*x+b)
    plt.title(symbol)

def get_trend_slope(df, symbol):
    x=np.array([n for n in range(0,len(df[df['Symbol']==symbol]))])
    y=np.array(df[df['Symbol']==symbol]['Close'])
    a, b = np.polyfit(x, y, 1)
    return a

def find_positive_trends(df, bol_df):
    """
    returns the symbols with positive trend slopes over the history of the data
    """
    for symbol in df['Symbol'].unique():
        a = get_trend_slope(bol_df, symbol)
        if a > 0:
            print(f'{symbol} a greater than 0: {a}')
            
def trend_slope(df, bol_df, symbol_col):
    for symbol in bol_df[symbol_col].unique():
        a = get_trend_slope(bol_df, symbol)
        idx = df[df[symbol_col] == symbol].index
        df.loc[idx, 'trend_slope'] = a
    return df
            
def n_day_moving_average(df, rolling_window):
    """
    Calculates and creates twenty day moving average values into the dataframe
    """
    # reset the index to an array
    df.reset_index(inplace=True)
    for symbol in df['Symbol'].unique():
        # get min and max index references to pass to .loc later
        idx_ref_min = min(df[df['Symbol']==symbol].index)
        idx_ref_max = max(df[df['Symbol']==symbol].index)
        
        close_series = df[df['Symbol']==symbol]['Close']
        rolling = close_series.rolling(window=rolling_window)
        twenty_day_rolling = rolling.mean()
        
        # set twenty day rolling average at proper indexes for given symbol
        df.loc[idx_ref_min:idx_ref_max+1,f'optimum_day_moving_average'] = twenty_day_rolling
        
    df.set_index('Date', inplace=True)
    return df
     
# def bolinger_bands(df, rolling_avg_col, rolling_window):
#     """
#     Calculates and creates bolinger band values (upper and lower) into the dataframe
#     """
#     # reset the index to an array
#     df.reset_index(inplace=True)
#     for symbol in df['Symbol'].unique():
#         # get min and max index references to pass to .loc later
#         idx_ref_min = min(df[df['Symbol']==symbol].index)
#         idx_ref_max = max(df[df['Symbol']==symbol].index)
        
#         n_day_rolling = df[df['Symbol']==symbol][rolling_avg_col].rolling(window=rolling_window)
#         standard_dev = n_day_rolling.std()
        
#         # set twenty day rolling average at proper indexes for given symbol
#         df.loc[idx_ref_min:idx_ref_max+1,'bolinger_upper_band'] = df.loc[idx_ref_min:idx_ref_max+1,rolling_avg_col] + standard_dev*2
#         df.loc[idx_ref_min:idx_ref_max+1,'bolinger_lower_band'] = df.loc[idx_ref_min:idx_ref_max+1,rolling_avg_col] - standard_dev*2
        
#     df.set_index('Date', inplace=True)

#     return df       


def plotly_plot_bolinger(df, symbol, window):
    pd.options.plotting.backend = "plotly"
    # fig = df[df['Symbol']==symbol][['Close', f'{window}_day_moving_average', 'bolinger_upper_band', 'bolinger_lower_band']].plot(title=symbol)
    x_axis=df[df['Symbol']==symbol].index
    fig = go.Figure(
        go.Scatter(x=x_axis, y=df[df['Symbol']==symbol]['Close'], 
                    name='Close Price'),
        layout={'title':f'{symbol}'}
        )
    fig.add_trace(
        go.Scatter(x=x_axis, y=df[df['Symbol']==symbol][f'optimum_day_moving_average'], 
                    name='Moving Average')
        )
    fig.add_trace(
        go.Scatter(x=x_axis, y=df[df['Symbol']==symbol][f'bolinger_upper_band'], 
                    name='Upper Band')
    )
    fig.add_trace(
        go.Scatter(x=x_axis, y=df[df['Symbol']==symbol][f'bolinger_lower_band'], 
                    name='Lower Band')
    )
    return fig

######################### News Article Analysis ###############################
import nltk
from nltk import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
 
# Dict subclass for counting hashable items. Sometimes called a bag or multiset. Elements are stored as dictionary keys and their counts are stored as dictionary values.
from collections import Counter

import re
        
def is_ok(token):
    stop = set(stopwords.words('english'))
    return re.match('^[a-z]+$', token) and token not in stop

def tokenize(sent):
    return [word for word in word_tokenize(sent) if is_ok(word)]

class News():
    def __init__(self, ticker):
        self.ticker = yf.Ticker(ticker)
        
    # scrape URL Links from news
    def get_urls(self):
        urls = [self.ticker.news[count]['link'] for count, value in enumerate(self.ticker.news)]
        return urls

    def get_titles(self):
        titles = [self.ticker.news[count]['title'] for count, value in enumerate(self.ticker.news)]
        return titles

    def get_publishers(self):
        publishers = [self.ticker.news[count]['publisher'] for count, value in enumerate(self.ticker.news)]
        return publishers

    def get_publish_times(self):
        publish_times = [self.ticker.news[count]['providerPublishTime'] for count, value in enumerate(self.ticker.news)]
        return publish_times

    def get_types(self):
        article_types = [self.ticker.news[count]['type'] for count, value in enumerate(self.ticker.news)]
        return article_types

class Article:
    def __init__(self, url):
       # get the articles
       self.contents = self.get_article_contents(url)
       
    def get_article_contents(self, url):
        """Gets the full text of a given Yahoo Finance article given by the url"""
        r = requests.get(url).text
        soup = BeautifulSoup(r, 'html.parser')

        p = soup.find_all('p')

        p_list = [text.get_text() for text in p]
        full_text = ' '.join(p_list)

        return full_text

    def summarize(text, n=5):
        # Tokenize the sentence
        sents = sent_tokenize(text.contents)
        # Get a "bill of words" or all words in all sentences that is_ok() 
        bow = [tokenize(sent) for sent in sents]
        # create a counter object to be used to count the words
        tf = Counter()

        # Iterate through the sentences in the bow
        for sent in bow:
            tf.update(sent)

        def score(i):
            return sum(tf[word] for word in bow[i])

        idx = sorted(range(len(bow)), key=score, reverse=True)[:n]
        summary_list = [sents[i] for i in idx]
        summary_text = ' '.join(summary_list)
        fail = 'Our engineers are working quickly to resolve the issue.'
        if summary_text != fail:
            return summary_text
        
    def polarity_scores(self):
        if self.contents != 'Thank you for your patience. Our engineers are working quickly to resolve the issue.':
            self.polarity_score = SentimentIntensityAnalyzer().polarity_scores(self.contents)
            return self.polarity_score
        else:
            return 'No article contents found.'




