from flask import Flask, render_template, redirect, url_for
import pandas as pd
import json
import plotly
import analysis
import plotly.graph_objects as go
import sqlite3
import os
from datetime import datetime, date, time

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
    
    return render_template('home.html',
                           tables=[
                               today_results_df
                               .sort_values(
                                   ['trend_slope'], 
                                   ascending=False)
                               .to_html(classes='data',
                                        formatters={'Symbol':link_frmt},
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
                                     '20_day_moving_average', 
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


@app.route("/showLineChart/<symbol>")
def showLineChart(symbol):
    # connect to and read the db table
    conn = get_db_connection()
    bol_df = read_bol_df()

    # create the plot object (trace)
    trace = analysis.plotly_plot_bolinger(bol_df, symbol, 20)
    
    # encode the plot object into json
    graphJSON = json.dumps(trace, cls=plotly.utils.PlotlyJSONEncoder)
    
    articles = analysis.News(symbol)
    titles = articles.get_titles()
    urls = articles.get_urls()
    link_dict = {}
    for idx, val in enumerate(titles):
        link_dict[titles[idx]] = urls[idx]
    
    
    return render_template('stock_page.html',
                           graphJSON=graphJSON,
                           symbol=symbol,
                           link_dict=link_dict)
    
@app.route('/data')
def data():
    conn = get_db_connection()
    bol_df = read_bol_df()
    return render_template('dataset.html',  
                           tables=[bol_df.to_html(classes='data')], 
                           titles=bol_df.columns.values)

