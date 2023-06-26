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
    return pd.read_sql('SELECT * FROM today_results',
                       con=get_db_connection(),
                       index_col='Symbol')

def get_today(): 
    return date.today()

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
    
    return render_template('home.html',
                           tables=[today_results_df.sort_values(['trend_slope'], ascending=False).to_html(classes='data')], 
                           values=today_results_df.columns.values,
                           today=get_today())

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


@app.route("/showLineChart")
def showLineChart():
    conn = get_db_connection()
    
    # make a graph
    bol_df = read_bol_df()
    trace = analysis.plotly_plot_bolinger(bol_df, bol_df['ticker'][0], 20)
    data = [trace]
    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('index.html',
                           graphJSON=graphJSON)
    
@app.route('/data')
def data():
    conn = get_db_connection()
    bol_df = read_bol_df()
    return render_template('simple.html',  
                           tables=[bol_df.to_html(classes='data')], 
                           titles=bol_df.columns.values)
