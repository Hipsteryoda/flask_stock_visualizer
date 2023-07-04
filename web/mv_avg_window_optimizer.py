import yfinance as yf
import pandas as pd
import numpy as np

def add_lag_price(df):
    df['price'] = df['Open'].shift(-1)
    return df
    
# Two classes
## One for a single parameter window optimizer
## The other for a two parameter window optimizer
class Single_Parameter_Optimizer:
    def __init__(self, df):
        self.df = add_lag_price(df)
        self.opts = self.optimize_window()
        self.optimum_window = self.opts[0]
        self.optimum_multiple = self.opts[1]

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