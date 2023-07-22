import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime

def add_lag_price(df):
    df['price'] = df['Open'].shift(-1)
    return df
    


#TODO:
## - [x] have Optimized_Symbol connect to database
## - [x] have Optimized_Symbol check if ticker has information on symbol in database
## - [] If info exists on symbol, use it rather than recalculate
##  - [] Return timestamp of data
## - [x] Else if info does not exist, calculate



class Optimized_Symbol:
    def __init__(self, symbol, period="12mo"):
        self.symbol = symbol.upper()
        # get optimized paramaters for symbol from database
        self.opt_param_df = self.query_db()
        # check if optimized params exist
        if self.opt_param_df.iloc[0,0] == None:
            # calculate
            self.history = yf.Ticker(symbol).history()
            self.single_param_opt = self.Single_Parameter_Optimizer(self.history)
            self.multi_param_opt = self.Multiple_Parameter_Optimizer(self.history)
            # write to db
            self.write_to_db()
        
    def get_db_connection(self):
        conn = sqlite3.connect('db/database.db')
        conn.row_factory = sqlite3.Row
        return conn
    
    def query_db(self):
        opt_params_df = pd.read_sql_query(f"""SELECT MAX(datetime), opt_single_ma_window, opt_two_ma_window_1, opt_two_ma_window_2
                FROM symbol_param_optimized
                WHERE symbol = '{self.symbol}';""",
                con=self.get_db_connection())
        return opt_params_df
    
    def write_to_db(self):
            payload = pd.DataFrame({'symbol':self.symbol,
            'datetime':datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
            'opt_single_ma_window':self.single_param_opt.optimum_window,
            'opt_single_multiple':self.single_param_opt.optimum_multiple,
            'opt_two_ma_window_1':self.multi_param_opt.optimum_window_1,
            'opt_two_ma_window_2':self.multi_param_opt.optimum_window_2,
            'opt_two_multiple':self.multi_param_opt.optimum_multiple,
            'organic_growth':self.single_param_opt.organic_growth},
            index=[0])
            payload.to_sql('symbol_param_optimized',
                           con=self.get_db_connection(),
                           if_exists='append',
                           index=False)
    
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