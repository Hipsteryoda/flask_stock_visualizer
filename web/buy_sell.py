from mv_avg_window_optimizer import Optimized_Symbol, add_lag_price

import pandas as pd
import numpy as np

import yfinance as yf

import psycopg2

from tqdm import tqdm

from datetime import date

def create_db_connection():
    conn = psycopg2.connect("dbname=stock_app user=stock_app password=stock_app_pi")
    cur = conn.cursor()
    return conn, cur

def close_db_connection(conn, cur):
    cur.close()
    conn.close()

def get_symbol_optimum_multiple(symbol):
    conn, cur = create_db_connection()
    query = f"""SELECT single_param_optimum_multiple, exp_ma_optimum_multiple
    FROM optimum_symbol_parameters
    WHERE symbol = '{symbol}';
    """
    cur.execute(query)
    results = cur.fetchall()[0]
    multiple_dict = dict(
        single_param_optimum_multiple = results[0],
        exp_ma_optimum_multiple = results[1]
    )
    multiple_dict = { k: (0 if v is None else v) for k, v in multiple_dict.items() }
    close_db_connection(conn, cur)
    # return the key for the maximum value as well as the maximum value
    return max(multiple_dict, key=multiple_dict.get)

def get_symbol_optimum_window(opt_mult, symbol):
    conn, cur = create_db_connection()
    optimum = opt_mult.replace('multiple', 'window')
    query = f"""SELECT {optimum} FROM optimum_symbol_parameters
    WHERE symbol = '{symbol}';"""
    cur.execute(query)
    optimum_window = cur.fetchall()[0][0]
    close_db_connection(conn, cur)
    return optimum_window

def calc_ma_price(how, symbol) -> pd.DataFrame:
    try:
        ticker = yf.Ticker(f'{symbol}')
        history = ticker.history(period='12mo')
        # current_price = yf.Ticker(symbol).basic_info['lastPrice']
        ma_df = add_lag_price(history)
        optimum_window = get_symbol_optimum_window(how, symbol)
        if how == 'single_param_optimum_multiple':
            ma_df['single_sma'] = ma_df.price.rolling(optimum_window).mean()
            ma_df['position'] = np.where(ma_df['price'] > ma_df['single_sma'], 'buy', 'sell')
                
        elif how == 'exp_ma_optimum_multiple':
            ma_df['exp_ma'] = ma_df.price.ewm(span=optimum_window, adjust=False).mean()
            ma_df['position'] = np.where(ma_df['price'] > ma_df['exp_ma'], 'buy', 'sell')
            
        # check if position today has changed from the previous day
        changed_from_yesterday = True if ma_df['position'].iloc[-1] != ma_df['position'].iloc[-2] else False
        return [ma_df['position'].iloc[-2], ma_df['price'].iloc[-2], changed_from_yesterday]
    except Exception as e:
        print(e)

def update_positions(symbol, position):
    if position != None:
        conn, cur = create_db_connection()
        query = f"""INSERT INTO positions (position, symbol, date, at_price, changed_from_yesterday)
        VALUES  ('{position[0]}', '{symbol}', '{date.today()}', '{position[1]}', '{position[2]}');
        """
        cur.execute(query)
        conn.commit()
        close_db_connection(conn, cur)
    else:
        print(f'Failed to update on {symbol}')
    

conn, cur = create_db_connection()
# get the current list of all symbols in the db
cur.execute("SELECT symbol FROM optimum_symbol_parameters;")
symbol_list = [val[0] for idx, val in enumerate(cur.fetchall())]
close_db_connection(conn, cur)

# for a given stock
#for symbol in tqdm(symbol_list):
for symbol in symbol_list:
    # find the historical best moving average performance and it's value
    opt_param = get_symbol_optimum_multiple(symbol)

    # calculate the optimum ma price for today
    position = calc_ma_price(opt_param, symbol)

    update_positions(symbol, position)



