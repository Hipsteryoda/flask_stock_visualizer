# Yahoo Finance API
import yfinance as yf

# Data manipulation stuff
import pandas as pd
import numpy as np

# Database Stuff
import sqlite3, psycopg2
from sqlalchemy import create_engine

# Plotting stuff
import plotly
import plotly.graph_objects as go

# Other
from datetime import datetime

import logging

# logging.basicConfig(level=logging.INFO, filename='logs/app.log', filemode='a', format='%(asctime)s: %(name)s - %(levelname)s - %(message)s')

##################################

def add_lag_price(df):
    df['price'] = df['Open'].shift(-1)
    return df

class Optimized_Symbol:
    def __init__(self, symbol, period="12mo"):
        logging.debug(f'Instantiating Optimized_Symbol with values: symbol={symbol}, period={period}')
        self.symbol = symbol.upper()
        self.calc_period = period
        self.history = yf.Ticker(self.symbol).history(period=period)
        
        # TODO: check db first before calculating
        if self.check_exists_in_db():
            logging.info(f'Symbol {self.symbol} exists in the table optimized_symbol_parameters')
            self.read_from_db()
            logging.info('Symbol details read from optimized_symbol_parameters')
        else:
            logging.debug(f'Calculating optimized parameters for new symbol {self.symbol}')
            self.single_param_opt = self.Single_Parameter_Optimizer(self.history)
            self.multi_param_opt = self.Multiple_Parameter_Optimizer(self.history)
            self.exp_ma_opt = self.Exponential_Moving_Average_Optimizer(self.history)
            self.write_to_db()
            self.read_from_db()
            
    def refresh(self):
        logging.info(f'Updating optimized parameters for symbol {self.symbol}')
        self.single_param_opt = self.Single_Parameter_Optimizer(self.history)
        self.multi_param_opt = self.Multiple_Parameter_Optimizer(self.history)
        self.exp_ma_opt = self.Exponential_Moving_Average_Optimizer(self.history)
        self.write_to_db()
        self.read_from_db()

    def create_db_connection(self):
        conn = psycopg2.connect("dbname=stock_app user=stock_app password=stock_app_pi")
        cur = conn.cursor()
        logging.debug("Created connection and cursor for: dbname=stock_app user=stock_app")
        return conn, cur

    def close_db_connection(self, conn, cur):
        cur.close()
        conn.close()
        logging.debug("Closed cursor and connection to database")
        
        
    def check_exists_in_db(self):
        query = f'''
        SELECT symbol_id FROM optimum_symbol_parameters
        WHERE symbol = '{self.symbol}';
        '''
        conn, cur = self.create_db_connection()
        cur.execute(query)
        if len(cur.fetchall()) == 0:
            logging.info(f'Symbol {self.symbol} does not exist in table optimized_symbol_parameters')
            self.close_db_connection(conn,cur)
            return False
        else:
            self.close_db_connection(conn,cur)
            return True
        
    def read_from_db(self):
        query = f'''
        SELECT * FROM optimum_symbol_parameters
        WHERE symbol = '{self.symbol}';
        '''
        conn, cur = self.create_db_connection()
        cur.execute(query)
        params = cur.fetchall()
        self.symbol_id = params[0][0]
        self.last_updated = params[0][2]
        self.calc_period = params[0][3]
        self.single_param_optimum_window = params[0][4]
        self.single_param_optimum_multiple = params[0][5]
        self.multi_param_optimum_window_1 = params[0][6]
        self.multi_param_optimum_window_2 = params[0][7]
        self.multi_param_optimum_multiple = params[0][8]
        self.organic_growth = params[0][9]
        self.exp_ma_optimum_window = params[0][10]
        self.exp_ma_optimum_multiple = params[0][11]
        self.close_db_connection(conn, cur)
        # return params      
    
    def write_to_db(self):
        """
        Writes data from Single and Multi param optimizations to database.
        First checks if symbol exists in `optimum_symbol_parameters`.
        If symbol exists, updates existing row.
        If symbol does not exist, inserts data in new row.
        """
        
        period = self.calc_period
        conn, cur = self.create_db_connection()
        
        insert_query = f'''
        INSERT INTO optimum_symbol_parameters
        (symbol, last_updated, calc_period, single_param_optimum_window,
        single_param_optimum_multiple, multi_param_optimum_window_1,
        multi_param_optimum_window_2, multi_param_optimum_multiple,
        organic_growth, exp_ma_optimum_window, exp_ma_optimum_multiple)
        VALUES
        ('{self.symbol.upper()}', '{datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")}',
        '{period}', {self.single_param_opt.optimum_window}, {self.single_param_opt.optimum_multiple},
        {self.multi_param_opt.optimum_window_1}, {self.multi_param_opt.optimum_window_2},
        {self.multi_param_opt.optimum_multiple}, {self.single_param_opt.organic_growth},
        {self.exp_ma_opt.optimum_window}, {self.exp_ma_opt.optimum_multiple})
        '''
        update_query = f'''
        UPDATE optimum_symbol_parameters
        SET last_updated='{datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")}',
        calc_period='{self.calc_period}',
        single_param_optimum_window={self.single_param_opt.optimum_window},
        single_param_optimum_multiple={self.single_param_opt.optimum_multiple},
        multi_param_optimum_window_1={self.multi_param_opt.optimum_window_1},
        multi_param_optimum_window_2={self.multi_param_opt.optimum_window_2},
        multi_param_optimum_multiple={self.multi_param_opt.optimum_multiple},
        organic_growth={self.single_param_opt.organic_growth},
        exp_ma_optimum_window={self.exp_ma_opt.optimum_window},
        exp_ma_optimum_multiple={self.exp_ma_opt.optimum_multiple}
        WHERE symbol = '{self.symbol}';'''
        
        select_query = f'''
        SELECT * FROM optimum_symbol_parameters
        WHERE symbol = '{self.symbol}';'''
        
        # check if symbol exists in table
        cur.execute(select_query)
        if len(cur.fetchall()) > 0:
            # then the symbol exists
            # use the update_query
            cur.execute(update_query)
        else:
            # use insert query
            cur.execute(insert_query)

        #commit changes
        conn.commit()

        # close connection
        self.close_db_connection(conn, cur)
            
    def refresh_data(self):
        """
        Caclulates the newest single and multi param optimizations and then writes to database
        """
        # calculate information
        self.history = yf.Ticker(self.symbol).history()
        self.single_param_opt = self.Single_Parameter_Optimizer(self.history)
        self.multi_param_opt = self.Multiple_Parameter_Optimizer(self.history)
        ## Uncomment to automatically write to database
        # self.write_to_db()
    
    def two_ma_calc(self, single_sma, multi_sma_1, multi_sma_2, exp_ma) -> pd.DataFrame:
        ma_df = add_lag_price(self.history.copy())
        ma_df['single_sma'] = ma_df.price.rolling(single_sma).mean()
        ma_df['multi_sma_1'] = ma_df.price.rolling(multi_sma_1).mean()
        ma_df['multi_sma_2'] = ma_df.price.rolling(multi_sma_2).mean()
        ma_df['exp_ma'] = ma_df.price.ewm(span=exp_ma, adjust=False).mean()
        # if Close > single_sma, in_position = True; else in_position = False
        ma_df['single_sma_in_position'] = np.where(ma_df['price'] > ma_df['single_sma'], True, False)
        ma_df['multi_sma_in_position'] = np.where(ma_df['multi_sma_1'] > ma_df['multi_sma_2'], True, False)
        ma_df['exp_sma_in_position'] = np.where(ma_df['price'] > ma_df['exp_ma'], True, False)
        # write ma_df to db
        return ma_df
    
    def write_ma_df_to_db(self):
        ma_df = add_lag_price(self.history.copy())
        ma_df['symbol_id'] = self.symbol_id
        engine = create_engine('postgresql+psycopg2://stock_app:superSecurePassword@localhost:5432/stock_app?')
        ma_df.to_sql('price_data', engine, if_exists='append')
    
    def plot_custom_ma(self):
        # get single, multi_1, and multi_2 params for symbol from db
        conn, cur = self.create_db_connection()
        query = f'''
        SELECT single_param_optimum_window, multi_param_optimum_window_1, multi_param_optimum_window_2, exp_ma_optimum_window, calc_period
        FROM optimum_symbol_parameters
        WHERE symbol = '{self.symbol}';
        '''
        cur.execute(query)
        results = cur.fetchall()
        single_param_optimum_window = results[0][0]
        multi_param_optimum_window_1 = results[0][1]
        multi_param_optimum_window_2 = results[0][2]
        exp_ma_optimum_window = results[0][3]
        calc_period = results[0][4]
        
        # reused from mv_avg_window_optimizer.Multiple_Parameter_Optimizer.two_ma_calc()
        ma_df = self.two_ma_calc(single_param_optimum_window, multi_param_optimum_window_1, multi_param_optimum_window_2, exp_ma_optimum_window)
        
        # plot the stuff
        x_axis=ma_df.index
        fig = go.Figure(
            go.Scatter(x=x_axis, y=ma_df['Close'], 
                        name='Close Price'),
            layout={'title':f'{self.symbol}'}
            )
        fig.add_trace(
            go.Scatter(x=x_axis, y=ma_df['single_sma'], 
                        name=f'{single_param_optimum_window} Day Moving Average (single)')
            )
        fig.add_trace(
            go.Scatter(x=x_axis, y=ma_df['multi_sma_1'], 
                        name=f'{multi_param_optimum_window_1} Day Moving Average (multi_1)')
        )
        fig.add_trace(
            go.Scatter(x=x_axis, y=ma_df['multi_sma_2'], 
                        name=f'{multi_param_optimum_window_2} Day Moving Average (multi_2)')
        )
        fig.add_trace(
            go.Scatter(x=x_axis, y=ma_df['exp_ma'],
                       name=f'{exp_ma_optimum_window} Day Exp. Moving Average (exp_ma)')
        )
        fig.add_trace(
            go.Scatter(x=x_axis, y=ma_df['Close'], mode='markers', marker_color=ma_df['single_sma_in_position'].astype(int),
                       name='Single SMA Buy/Sell')
        )
        fig.add_trace(
            go.Scatter(x=x_axis, y=ma_df['Close'], mode='markers', marker_color=ma_df['multi_sma_in_position'].astype(int),
                       name='Multi SMA Buy/Sell')
        )
        fig.add_trace(
            go.Scatter(x=x_axis, y=ma_df['Close'], mode='markers', marker_color=ma_df['exp_sma_in_position'].astype(int),
                       name='Exp. MA Buy/Sell')
        )
        # fig.show()
        
        self.close_db_connection(conn, cur)
        return fig
    
    # Two classes
    ## One for a single parameter window optimizer
    ## The other for a two parameter window optimizer
    class Single_Parameter_Optimizer:
        def __init__(self, df):
            logging.debug(f'Initializing Single_Parameter_Optimizer')
            self.df = add_lag_price(df)
            self.opts = self.optimize_window()
            self.optimum_window = self.opts[0]
            self.optimum_multiple = self.opts[1]
            self.organic_growth = (df.Close.pct_change()+1).prod()
            logging.debug(f"""Finished Single_Parameter_Optimizer initialization with values:
                          Optimum Window: {self.optimize_window}""")

        # Moving Average calculation
        def ma_calc(self, n):
            self.df['sma'] = self.df.Close.rolling(n).mean()
    
        def backtest(self, df, n, how='multiple'):
            # data manipulation to the dataframe
            self.ma_calc(n)
            
            in_position = False
            
            profits = []
            
            for index, row in df.iterrows():
                if not in_position:
                    if row.Close > row.sma:
                        buyprice = row.price
                        in_position = True
                        
                if in_position:
                    if row.Close < row.sma:
                        # calculate relative profit
                        profit = (row.price - buyprice)/buyprice
                        profits.append(profit)
                        in_position = False

            if how == 'multiple':
                # returns a number that is a multiplier of your capital
                overall_profit = (pd.Series(profits) + 1).prod()
            if how == 'percentage':
                overall_profit = (((pd.Series(profits) + 1).prod())-1)*100
            return round(overall_profit, 3)

        def optimize_window(self):
            calcs = {}
            # calculate all moving average windows inside of a year in one day steps
            for n in range(5, 366, 5):
                calcs[n] = self.backtest(self.df, n)
                
            calcs_series = pd.Series(calcs)
            
            # calculate the optimum window and what the multiple of initial capital would be
            maxidx = calcs_series.idxmax()
            maxval = calcs_series.loc[maxidx]
            opt = (maxidx, maxval)
            return opt
            
    class Multiple_Parameter_Optimizer:
        def __init__(self, df):
            self.df = add_lag_price(df)
            self.opts = self.optimize_window()
            self.optimum_window_1 = self.opts[0][0]
            self.optimum_window_2 = self.opts[0][1]
            self.optimum_multiple = self.opts[1]
            self.organic_growth = (df.Close.pct_change()+1).prod()

        def two_ma_calc(self, n, m):
            self.df['sma_1'] = self.df.Close.rolling(n).mean()
            self.df['sma_2'] = self.df.Close.rolling(m).mean()

        def two_backtest(self, df, n, m, how='multiple'):
            # data manipulation to the dataframe
            self.two_ma_calc(n, m)
            
            in_position = False
            
            profits = []
            
            for index, row in df.iterrows():
                if not in_position:
                    if row.sma_1 > row.sma_2:
                        buyprice = row.price
                        in_position = True
                        
                if in_position:
                    if row.sma_1 < row.sma_2:
                        # calculate relative profit
                        profit = (row.price - buyprice)/buyprice
                        profits.append(profit)
                        in_position = False

            if how == 'multiple':
                # returns a number that is a multiplier of your capital
                overall_profit = (pd.Series(profits) + 1).prod()
            if how == 'percentage':
                overall_profit = (((pd.Series(profits) + 1).prod())-1)*100
            return round(overall_profit, 3)
        
        def optimize_window(self):
            # get all combinations of windows
            x = pd.DataFrame(np.arange(10, 365, 5))
            y = pd.DataFrame(np.arange(10, 365, 5))

            final = pd.merge(x, y, how='cross')
            final.columns = ['sma_1', 'sma_2']
            # don't need rows where n and m window are the same
            final = final[final.sma_1 != final.sma_2]
            
            two_param_calcs_df = pd.DataFrame()
            for n, m in final.values:
                two_param_calcs_df.loc[n, m] = self.two_backtest(self.df, n, m)
                
            two_param_calcs_df.fillna(0, inplace=True)
            # axis 0 looks for the idxmax for n, axis 1 looks for the idxmax of m
            optimum_windows = two_param_calcs_df.max(axis=0).idxmax(), two_param_calcs_df.max(axis=1).idxmax()
            optimized_multiple = two_param_calcs_df.loc[optimum_windows[0], optimum_windows[1]]
            return optimum_windows, optimized_multiple
        
    class Exponential_Moving_Average_Optimizer:
        def __init__(self, df):
            self.df = add_lag_price(df)
            self.opts = self.optimize()
            self.optimum_window = self.opts[0]
            self.optimum_multiple = self.opts[1]
            self.organic_growth = (df.Close.pct_change()+1).prod()

        def ema_calc(self, n):
            # calculate ewm on Price
            self.df['exp_ma'] = self.df['price'].ewm(span=n, adjust=False).mean()
            

        def backtest(self, df, n, how='multiple'):
            self.ema_calc(n)
            in_position = False
            
            profits = []
            
            for index, row in df.iterrows():
                if not in_position:
                    if row['exp_ma'] > row['price']:
                        buyprice = row.price
                        in_position = True
                        
                if in_position:
                    if row['exp_ma'] < row['price']:
                        # calculate relative profit
                        profit = (row.price - buyprice)/buyprice
                        profits.append(profit)
                        in_position = False

            if how == 'multiple':
                # returns a number that is a multiplier of your capital
                overall_profit = (pd.Series(profits) + 1).prod()
            if how == 'percentage':
                overall_profit = (((pd.Series(profits) + 1).prod())-1)*100
            return round(overall_profit, 3)

        def optimize(self):
            calcs = {}
            # calculate all moving average windows inside of a year in one day steps
            for n in range(5, 366, 5):
                calcs[n] = self.backtest(self.df, n)
                
            calcs_series = pd.Series(calcs)
            
            # calculate the optimum window and what the multiple of initial capital would be
            maxidx = calcs_series.idxmax()
            maxval = calcs_series.loc[maxidx]
            opt = (maxidx, maxval)
            return opt