from flask import Flask, render_template, redirect, url_for
import pandas as pd
import json
import plotly
import analysis
import plotly.graph_objects as go
import sqlite3, psycopg2
import os
from datetime import datetime, date, time
from mv_avg_window_optimizer import Optimized_Symbol

import logging

logging.basicConfig(level=logging.INFO, 
                    filename='logs/app.log', 
                    filemode='a', 
                    format='%(asctime)s: %(name)s - %(levelname)s - %(message)s')

app = Flask(__name__)

########################################################################
# Functional stuff
def get_db_connection():
    conn = sqlite3.connect('db/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_psql_db_connection():
    conn = psycopg2.connect("dbname=stock_app user=ksmith")
    cur = conn.cursor()
    return conn, cur

def close_psql_db_connection(conn, cur):
    cur.close()
    conn.close()

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

def read_optimization_params(symbol):
    # retrieve latest info from db for parameter optimization
    query = f'''
    SELECT * FROM optimum_symbol_parameters
    WHERE symbol = '{symbol}';'''
    conn, cur = create_psql_db_connection()
    cur.execute(query)
    facts_table = pd.DataFrame(data=cur.fetchall(),
                               columns=['ID','Symbol','Last Updated','Calc Period',
                                        'Single SMA Optimum Window','Single SMA Optimum Multiple',
                                        'Multi SMA Optimum Window 1','Multi SMA Optimum Window 2',
                                        'Multi SMA Optimum Multiple','Organic Growth', 'Exponential MA Optimum Window',
                                        'Exponential MA Optimum Multiple'])
    close_psql_db_connection(conn, cur)
    return facts_table
    
def read_top_100_sma(sort_by='single'):
    '''
    Reads the top 100 stocks sorted by return multiple
    '''
    conn, cur = create_psql_db_connection()
    valid_sort_by = ['single', 'multi']
    if sort_by not in valid_sort_by:
        raise ValueError(f"Expected 'single' or 'multi'; got {sort_by}")
    
    query = """
    SELECT symbol_id, symbol, last_updated, calc_period,
    single_param_optimum_window, single_param_optimum_multiple, organic_growth 
    FROM optimum_symbol_parameters
    WHERE single_param_optimum_multiple IS NOT NULL
    ORDER BY single_param_optimum_multiple DESC
    LIMIT 100; 
    """
    
    cur.execute(query)
    table = pd.DataFrame(data=cur.fetchall(),
                         columns=['symbol_id','symbol','last_updated','calc_period',
                         'single_param_optimum_window','single_param_optimum_multiple','organic_growth'])
    close_psql_db_connection(conn, cur)
    return table

def read_top_100_exp_ma():
    '''
    Reads the top 100 stocks sorted by return multiple
    '''
    conn, cur = create_psql_db_connection()
    
    query = """
    SELECT symbol_id, symbol, last_updated, calc_period,
    exp_ma_optimum_window, exp_ma_optimum_multiple, organic_growth 
    FROM optimum_symbol_parameters
    WHERE exp_ma_optimum_multiple IS NOT NULL
    ORDER BY exp_ma_optimum_multiple DESC
    LIMIT 100; 
    """
    
    cur.execute(query)
    table = pd.DataFrame(data=cur.fetchall(),
                         columns=['symbol_id','symbol','last_updated','calc_period',
                                  'exp_ma_optimum_window', 'exp_ma_optimum_multiple'
                                  ,'organic_growth'])
    close_psql_db_connection(conn, cur)
    return table
    

######################################################################### 

@app.route("/")
def root():
    logging.debug('Redirecting from root (/) to home (/home)')
    return redirect(url_for("home"))

@app.route("/index")
def index():
    return(render_template('index.html',
           title='YOUR TITLE HERE!'
           )
           )

@app.route("/home")
def home():
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
                           today=get_today(),
                           title="Stock App"
                           )

@app.route('/rebuild')
def rebuild():
    stockdata = analysis.StockData()
    bol_df = stockdata.bol_df

    conn = get_db_connection()
    bol_df.to_sql('bol_df', 
                  con=conn, 
                  if_exists='replace')
    
    today_results_df = analysis.trend_slope(stockdata.gainers_df, bol_df, 'Symbol')
    today_results_df.to_sql('today_results',
                            con=conn,
                            if_exists='replace')
    
    return redirect(url_for('home'))

@app.route("/optimization_refresh/<symbol>")
def optimization_refresh(symbol):
    Optimized_Symbol(symbol).refresh()
    return redirect('/showLineChart/' + symbol)

@app.route("/showLineChart/<symbol>")
def showLineChart(symbol):
    # Stock article stuff
    news = analysis.News(symbol)
    titles = news.get_titles()
    urls = news.get_urls()
    link_dict = {}
    for idx, val in enumerate(titles):
        link_dict[titles[idx]] = [urls[idx], analysis.Article(urls[idx]).polarity_scores()]
    
    # instantiate Optimized_Symbol
    opt = Optimized_Symbol(symbol)
    
    # TODO: update Optimized_Symbol to check db first before calculating attributes
    facts_table = read_optimization_params(symbol)
    
    # create the plot object (trace)
    trace = opt.plot_custom_ma()
    
    # encode the plot object into json
    graphJSON = json.dumps(trace, cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_template('stock_page.html',
                           title=symbol,
                           graphJSON=graphJSON,
                           symbol=symbol,
                           link_dict=link_dict,
                           refresh_opts=redirect('/optimization_refresh/' + symbol),
                           facts_table=facts_table.to_html(
                               index=False
                           ))
    
@app.route('/data')
def data():
    conn = get_db_connection()
    bol_df = read_bol_df()
    return render_template('dataset.html',  
                           tables=[bol_df.to_html()], 
                           titles=bol_df.columns.values,
                           title="All Data")

@app.route('/top_100_single_sma')
def top_100_single_sma():
    table = read_top_100_sma()
    table.set_index('symbol_id', inplace=True)

    link_frmt = lambda x: f'<a href="showLineChart/{x}">{x}</a>'
    hdr_frmt = f'<th onclick="something"></th>'
    
    return render_template('top_100_single_sma.html',
                           table=table.to_html(formatters={'symbol':link_frmt},
                                               escape=False,
                                               index=False),
                           title='Top 100 Single SMA')

@app.route('/top_100_exp_ma')
def top_100_exp_ma():
    table = read_top_100_exp_ma()
    table.set_index('symbol_id', inplace=True)

    link_frmt = lambda x: f'<a href="showLineChart/{x}">{x}</a>'
    hdr_frmt = f'<th onclick="something"></th>'
    
    return render_template('top_100_exp_ma.html',
                           table=table.to_html(formatters={'symbol':link_frmt},
                                               escape=False,
                                               index=False),
                           title='Top 100 Exponential MA')