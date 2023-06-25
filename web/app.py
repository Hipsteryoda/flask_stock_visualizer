from flask import Flask, render_template, redirect, url_for
import pandas as pd
import json
import plotly
import analysis
import plotly.graph_objects as go
import sqlite3

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('db/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def read_bol_df():
    bol_df = pd.read_sql('SELECT * FROM bol_df', 
                         con=get_db_connection(),
                         index_col='Date')
    return bol_df
    

@app.route("/home")
def home():
    bol_df = read_bol_df()
    home_df = pd.DataFrame(bol_df['ticker'].unique())
    
    return render_template('home.html',
                           tables=[home_df.to_html(classes='data')], 
                           titles=home_df.columns.values)

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
