from flask import Flask, render_template, redirect, url_for
import pandas as pd
import json
import plotly
import analysis
import plotly.graph_objects as go
import sqlite3
import os
from datetime import datetime, date, time
from mv_avg_window_optimizer import Single_Parameter_Optimizer, Multiple_Parameter_Optimizer

app = Flask(__name__)

########################################################################
# Functional stuff
def get_db_connection():
    conn = sqlite3.connect('db/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def read_bol_df():
    bol_df = pd.read_sql('SELECT * FROM bol_df', 
                         con=get_db_connection(),
                         index_col='Date')
    return bol_df

def read_today_results_df():
    df = pd.read_sql('SELECT * FROM today_results',
                       con=get_db_connection())
    df.loc[:,'Symbol':]
    return df 

def get_today(): 
    return date.today()


def get_summarized_articles():
    
    return ''

def post_optimization_params(symbol, period):
        single_opts = Single_Parameter_Optimizer(analysis.get_history(symbol, period))
        two_opts = Multiple_Parameter_Optimizer(analysis.get_history(symbol, period))
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
                       con=get_db_connection(),
                       if_exists='append',
                       index=False)

def read_optimization_params(symbol):
    # retrieve latest info from db for parameter optimization
    query = f'''SELECT * FROM symbol_param_optimized
WHERE datetime IN (SELECT max(datetime) FROM symbol_param_optimized WHERE symbol = '{symbol}');'''
    conn = get_db_connection()
    facts_table = pd.read_sql_query(
        sql=query,
        con=conn
    )
    return facts_table
    
# def refresh_opts(symbol):
#     period = '12mo'
#     post_optimization_params(symbol, period)
    

######################################################################### 

@app.route("/")
def root():
    return redirect(url_for("home"))

@app.route("/home")
def home():
    # bol_df = read_bol_df()
    # home_df = pd.DataFrame(bol_df['ticker'].unique())
    # home_df.columns = ['Symbol']
    
    today_results_df = read_today_results_df()
    link_frmt = lambda x: f'<a href="showLineChart/{x}">{x}</a>'
    hdr_frmt = f'<th onclick="something"></th>'
    
    return render_template('home.html',
                           tables=[
                               today_results_df
                               .sort_values(
                                   ['trend_slope'], 
                                   ascending=False)
                               .to_html(formatters={'Symbol':link_frmt},
                                        escape=False,
                                        index=False)
                               ], 
                           values=today_results_df.columns.values,
                           today=get_today()
                           )

@app.route('/rebuild')
def rebuild():
    # Get list of gainer stocks
    df = analysis.get_biggest_gainers()
    
    # Assemble their history
    built_df = analysis.build_stocks_df(df)

    # Get moving average and bolinger bands
    ma_df = analysis.n_day_moving_average(built_df, 20)
    bol_df = analysis.bolinger_bands(ma_df, 
                                     'optimum_day_moving_average', 
                                     20)

    conn = get_db_connection()
    bol_df.to_sql('bol_df', 
                  con=conn, 
                  if_exists='replace')
    
    today_results_df = analysis.trend_slope(df, bol_df, 'Symbol')
    today_results_df.to_sql('today_results',
                            con=conn,
                            if_exists='replace')
    
    return redirect(url_for('home'))

@app.route("/optimization_refresh/<symbol>")
def optimization_refresh(symbol):
    post_optimization_params(symbol, '12mo')
    # refresh_opts(symbol)
    # return redirect('/showLineChart/' + symbol)

@app.route("/showLineChart/<symbol>")
def showLineChart(symbol):
    # connect to and read the db table
    conn = get_db_connection()
    bol_df = read_bol_df()
    facts_table = read_optimization_params(symbol)
    period = '12mo'
    if facts_table.shape[0] == 0:
        # get and post params
        post_optimization_params(symbol, period)
        facts_table = read_optimization_params(symbol)


    # Stock article stuff
    news = analysis.News(symbol)
    titles = news.get_titles()
    urls = news.get_urls()
    link_dict = {}
    for idx, val in enumerate(titles):
        link_dict[titles[idx]] = [urls[idx], analysis.Article(urls[idx]).polarity_scores()]
    
    # create the plot object (trace)
    trace = analysis.plotly_plot_bolinger(bol_df, symbol, facts_table.opt_single_ma_window)
    
    # encode the plot object into json
    graphJSON = json.dumps(trace, cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_template('stock_page.html',
                           graphJSON=graphJSON,
                           symbol=symbol,
                           link_dict=link_dict,
                           refresh_opts=redirect('/optimization_refresh/' + symbol),
                           facts_table=facts_table.to_html(
                               index=False,
                               classes='center'
                           ))
    
@app.route('/data')
def data():
    conn = get_db_connection()
    bol_df = read_bol_df()
    return render_template('dataset.html',  
                           tables=[bol_df.to_html(classes='data')], 
                           titles=bol_df.columns.values)

