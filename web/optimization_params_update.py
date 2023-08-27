from mv_avg_window_optimizer import Optimized_Symbol, add_lag_price
import pandas as pd
from tqdm import tqdm


stocks = pd.read_csv('/home/ksmith/flask_stock_visualizer/web/nasdaq_screener_1690226089920.csv')

stock_list = stocks.Symbol.to_list()

for symbol in stock_list:
    Optimized_Symbol(symbol)