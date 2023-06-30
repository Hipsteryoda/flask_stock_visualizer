import requests
import pandas as pd
import numpy as np

import yfinance as yf

import matplotlib.pyplot as plt

from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
pio.renderers.default = "browser"

def get_biggest_gainers() -> pd.DataFrame:
    r = requests.get('https://www.dogsofthedow.com/biggest-stock-gainers-today.htm')
    gainers_df = pd.read_html(r.text)[0]
    return gainers_df

def get_history(ticker, period):
    t = yf.Ticker(ticker)
    return t.history(period)

def build_stocks_df(gainers_df) -> pd.DataFrame:
    loop = 0
    period = "12mo"
    for s in gainers_df['Symbol']:
        if loop == 0:
            df = get_history(s, period=period)
            df['ticker'] = s
            loop +=1
        else:
            temp_df = get_history(s, period=period)
            temp_df['ticker'] = s
            df = pd.concat([df, temp_df])
            
    return df

def graph_trend(df, symbol):
    x=np.array([n for n in range(0,len(df[df['ticker']==symbol]))])
    y=np.array(df[df['ticker']==symbol]['Close'])
    a, b = np.polyfit(x, y, 1)
    df[df['ticker']==symbol]['Close'].plot()
    plt.plot(df[df['ticker']==symbol]['Close'].index, a*x+b)
    plt.title(symbol)

def get_trend_slope(df, symbol):
    x=np.array([n for n in range(0,len(df[df['ticker']==symbol]))])
    y=np.array(df[df['ticker']==symbol]['Close'])
    a, b = np.polyfit(x, y, 1)
    return a

def find_positive_trends(df, bol_df):
    """
    returns the symbols with positive trend slopes over the history of the data
    """
    for symbol in df['ticker'].unique():
        a = get_trend_slope(bol_df, symbol)
        if a > 0:
            print(f'{symbol} a greater than 0: {a}')
            
def trend_slope(df, bol_df, symbol_col):
    for symbol in df[symbol_col].unique():
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
    for symbol in df['ticker'].unique():
        # get min and max index references to pass to .loc later
        idx_ref_min = min(df[df['ticker']==symbol].index)
        idx_ref_max = max(df[df['ticker']==symbol].index)
        
        close_series = df[df['ticker']==symbol]['Close']
        rolling = close_series.rolling(window=rolling_window)
        twenty_day_rolling = rolling.mean()
        
        # set twenty day rolling average at proper indexes for given symbol
        df.loc[idx_ref_min:idx_ref_max+1,f'{rolling_window}_day_moving_average'] = twenty_day_rolling
        
    df.set_index('Date', inplace=True)
    return df
     
def bolinger_bands(df, rolling_avg_col, rolling_window):
    """
    Calculates and creates bolinger band values (upper and lower) into the dataframe
    """
    # reset the index to an array
    df.reset_index(inplace=True)
    for symbol in df['ticker'].unique():
        # get min and max index references to pass to .loc later
        idx_ref_min = min(df[df['ticker']==symbol].index)
        idx_ref_max = max(df[df['ticker']==symbol].index)
        
        n_day_rolling = df[df['ticker']==symbol][rolling_avg_col].rolling(window=rolling_window)
        standard_dev = n_day_rolling.std()
        
        # set twenty day rolling average at proper indexes for given symbol
        df.loc[idx_ref_min:idx_ref_max+1,'bolinger_upper_band'] = df.loc[idx_ref_min:idx_ref_max+1,rolling_avg_col] + standard_dev*2
        df.loc[idx_ref_min:idx_ref_max+1,'bolinger_lower_band'] = df.loc[idx_ref_min:idx_ref_max+1,rolling_avg_col] - standard_dev*2
        
    df.set_index('Date', inplace=True)

    return df       


def plotly_plot_bolinger(df, symbol, window):
    pd.options.plotting.backend = "plotly"
    # fig = df[df['ticker']==symbol][['Close', f'{window}_day_moving_average', 'bolinger_upper_band', 'bolinger_lower_band']].plot(title=symbol)
    x_axis=df[df['ticker']==symbol].index
    fig = go.Figure(
        go.Scatter(x=x_axis, y=df[df['ticker']==symbol]['Close'], 
                    name='Close Price'),
        layout={'title':f'{symbol}'}
        )
    fig.add_trace(
        go.Scatter(x=x_axis, y=df[df['ticker']==symbol][f'{window}_day_moving_average'], 
                    name='Moving Average')
        )
    fig.add_trace(
        go.Scatter(x=x_axis, y=df[df['ticker']==symbol][f'bolinger_upper_band'], 
                    name='Upper Band')
    )
    fig.add_trace(
        go.Scatter(x=x_axis, y=df[df['ticker']==symbol][f'bolinger_lower_band'], 
                    name='Lower Band')
    )
    return fig.show()
