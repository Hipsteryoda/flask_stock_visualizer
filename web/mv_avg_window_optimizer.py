# Yahoo Finance API
import yfinance as yf

# Data manipulation stuff
import pandas as pd
import numpy as np

# Database Stuff
import sqlite3, psycopg2

# Plotting stuff
import plotly
import plotly.graph_objects as go

# Other
from datetime import datetime

##################################

def add_lag_price(df):
    df['price'] = df['Open'].shift(-1)
    return df

class Optimized_Symbol:
    def __init__(self, symbol, period="12mo"):
        self.symbol = symbol.upper()
        self.calc_period = period
        self.history = yf.Ticker(self.symbol).history(period=period)
        
        # TODO: check db first before calculating
        if self.check_exists_in_db():
            self.read_from_db()
        else:
            self.single_param_opt = self.Single_Parameter_Optimizer(self.history)
            self.multi_param_opt = self.Multiple_Parameter_Optimizer(self.history)
            self.write_to_db()
            self.read_from_db()

    def create_db_connection(self):
        conn = psycopg2.connect("dbname=stock_app user=ksmith")
        cur = conn.cursor()
        return conn, cur

    def close_db_connection(self, conn, cur):
        cur.close()
        conn.close()
        
    def check_exists_in_db(self):
        query = f'''
        SELECT symbol_id FROM optimum_symbol_parameters
        WHERE symbol = '{self.symbol}';
        '''
        conn, cur = self.create_db_connection()
        cur.execute(query)
        if len(cur.fetchall()) == 0:
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
        self.last_updated = params[0][2]
        self.calc_period = params[0][3]
        self.single_param_optimum_window = params[0][4]
        self.single_param_optimum_multiple = params[0][5]
        self.multi_param_optimum_window_1 = params[0][6]
        self.multi_param_optimum_window_2 = params[0][7]
        self.multi_param_optimum_multiple = params[0][8]
        self.organic_growth = params[0][9]
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
        conn = psycopg2.connect("dbname=stock_app user=ksmith")
        cur = conn.cursor()
        
        insert_query = f'''
        INSERT INTO optimum_symbol_parameters
        (symbol, last_updated, calc_period, single_param_optimum_window,
        single_param_optimum_multiple, multi_param_optimum_window_1,
        multi_param_optimum_window_2, multi_param_optimum_multiple,
        organic_growth)
        VALUES
        ('{self.symbol.upper()}', '{datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")}',
        '{period}', {self.single_param_opt.optimum_window}, {self.single_param_opt.optimum_multiple},
        {self.multi_param_opt.optimum_window_1}, {self.multi_param_opt.optimum_window_2},
        {self.multi_param_opt.optimum_multiple}, {self.single_param_opt.organic_growth})
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
        organic_growth={self.single_param_opt.organic_growth}
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
        cur.close()
        conn.close()
            
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
    
    def two_ma_calc(self, single_sma, multi_sma_1, multi_sma_2) -> pd.DataFrame:
        ma_df = self.history.copy()
        ma_df['single_sma'] = ma_df.Close.rolling(single_sma).mean()
        ma_df['multi_sma_1'] = ma_df.Close.rolling(multi_sma_1).mean()
        ma_df['multi_sma_2'] = ma_df.Close.rolling(multi_sma_2).mean()
        return ma_df
    
    def plot_custom_ma(self):
        # get single, multi_1, and multi_2 params for symbol from db
        conn, cur = self.create_db_connection()
        query = f'''
        SELECT single_param_optimum_window, multi_param_optimum_window_1, multi_param_optimum_window_2, calc_period
        FROM optimum_symbol_parameters
        WHERE symbol = '{self.symbol}';
        '''
        cur.execute(query)
        results = cur.fetchall()
        single_param_optimum_window = results[0][0]
        multi_param_optimum_window_1 = results[0][1]
        multi_param_optimum_window_2 = results[0][2]
        calc_period = results[0][3]
        
        # reused from mv_avg_window_optimizer.Multiple_Parameter_Optimizer.two_ma_calc()
        ma_df = self.two_ma_calc(single_param_optimum_window, multi_param_optimum_window_1, multi_param_optimum_window_2)
        
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
        # fig.show()
        
        self.close_db_connection(conn, cur)
        return fig
    
    # Two classes
    ## One for a single parameter window optimizer
    ## The other for a two parameter window optimizer
    class Single_Parameter_Optimizer:
        def __init__(self, df):
            self.df = add_lag_price(df)
            self.opts = self.optimize_window()
            self.optimum_window = self.opts[0]
            self.optimum_multiple = self.opts[1]
            self.organic_growth = (df.Close.pct_change()+1).prod()

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
            return overall_profit

        def optimize_window(self):
            calcs = {}
            # calculate all moving average windows inside of a year in one day steps
            for n in range(1, 366):
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
            return overall_profit
        
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
            optimum_windows = two_param_calcs_df[two_param_calcs_df.max(axis=0).idxmax()].idxmax(), two_param_calcs_df.max(axis=0).idxmax()
            optimized_multiple = two_param_calcs_df.loc[optimum_windows[0], optimum_windows[1]]
            return optimum_windows, optimized_multiple