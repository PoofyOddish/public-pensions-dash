# Public Pension Dashboard - Application Code

#####################################
# Import needed packages
import pandas as pd
import numpy as np

import psycopg2
import sqlalchemy
import plotly
import plotly.graph_objects as go

import plotly.express as px
from sqlalchemy import create_engine

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output, State
from textwrap import dedent

#####################################
###Data collection + cleaning

# Connect to postgreSQL DB
conn = psycopg2.connect("dbname=jordan")

# Read in data from Heroku PostgresDB
test = pd.read_sql("SELECT fy,stateabbrev,actfundedratio_gasb,planname,totmembership,investmentreturnassumption_gasb FROM pensions",
                   conn)

# Close connection to DB
conn.close()

# Prepare data for grouping

#Convert later used features to float
test['totmembership']=test['totmembership'].astype(float)
test['actfundedratio_gasb']=test['actfundedratio_gasb'].astype(float)
test['investmentreturnassumption_gasb']=test['investmentreturnassumption_gasb'].astype(float)

#Create weighted values for merging to state level
test['weights_fundedratio'] = test['totmembership']*test['actfundedratio_gasb']
test['weights_investassume'] = test['totmembership']*test['investmentreturnassumption_gasb']

#Group pension data by fiscal year and state
## NB, not all pension plans are run on a fiscal year. Fiscal year is stated
## out of simplicity.
grouped = test.groupby(['fy','stateabbrev']).sum()

#####################################
#Prepare funded ratio data

#Calculate weighted average and rename features
grouped_fundedratio = ((grouped['weights_fundedratio']/grouped['totmembership'])*100).reset_index()
grouped_fundedratio.columns = ['fy','state','fundedratio']

#Create copy of df and round weighted ratio
ratio_map = grouped_fundedratio.copy()
ratio_map['fundedratio']=round(ratio_map['fundedratio'],2)

#Fill missing values with 0 for mapping
ratio_map['fundedratio']=ratio_map['fundedratio'].fillna(0)

#Calculate adjusted ratio for mapping - any value above 100 = 100, any value under 50 = 50
#This is temporary until I can get the color range working on the map
ratio_map['adj_ratio']=ratio_map['fundedratio'].where(ratio_map['fundedratio']<100,100)
ratio_map['adj_ratio']=ratio_map['adj_ratio'].where(ratio_map['adj_ratio']>50,50)

#Create new features for use in merging with granular plan data
ratio_map['planname']="State Average"
ratio_map['state_avg']=1

#Create new DF with all plan data
subset_plans=test[['fy','stateabbrev','actfundedratio_gasb','planname']]
subset_plans.columns = ['fy','state','fundedratio','planname']

#Multiply funded ratio by 100 to put on scale of 0 - 100+
subset_plans['fundedratio']=subset_plans['fundedratio']*100

#Create new feature to denote values are not state avg
subset_plans['state_avg']=0

#Append state averages and plan data together
all_ratio = ratio_map.append(subset_plans)

#Make sure all funded ratios are rounded to 2 decimal places for ease of reading
all_ratio['fundedratio']=round(all_ratio['fundedratio'],2)

#####################################
#Prepare Assumed Investment Return data

#Calculate weighted average and rename features
grouped_investassume = ((grouped['weights_investassume']/grouped['totmembership'])*100).reset_index()
grouped_investassume.columns = ['fy','state','assumed_investment']

#Create new features for use in merging with granular plan data
grouped_investassume['planname']="State Average"
grouped_investassume['state_avg']=1

#Create new DF with all plan data
subset_plans=test[['fy','stateabbrev','investmentreturnassumption_gasb','planname']]
subset_plans.columns = ['fy','state','assumed_investment','planname']

#Multiply funded ratio by 100 to put on scale of 0 - 100+
subset_plans['assumed_investment']=(subset_plans['assumed_investment']*100)

#Create new feature to denote values are not state avg
subset_plans['state_avg']=0

#Append state averages and plan data together
all_plans = grouped_investassume.append(subset_plans)

#Make sure all funded ratios are rounded to 2 decimal places for ease of reading
all_plans['assumed_investment']=round(all_plans['assumed_investment'],2)

#####################################
#Misc Data

#Used for dropdown menus in tabs
measures = ['Historical Funded Ratio',"Historical Annual Assumed Return"]

#####################################
#### DASH APP LAYOUT

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.config['suppress_callback_exceptions'] = True

app.layout = html.Div([

    html.Div([

        #Header Text
        html.H1(children="Public Pension Dashboard"),

        html.Hr(),

        #Markdown Text - above graphs under header
        html.Div([
            dcc.Markdown(dedent("""
            
            ## Overview

            This tool is meant to assist in quick analysis of trends in overall public pension funding. 📊
            
            Unless otherwise notated, all data is sourced from the [Public Plans Database](https://publicplansdata.org), created by Boston College's Center for Retirement Research.  

            To get started, hover over a state in the below map.
            Click on play button below map to see funded ratio over time.
            
            """))
        ],style={'marginLeft': 10, 'marginRight': 10, 'marginTop': 10, 'marginBottom': 10, 
                'backgroundColor':'#F7FBFE',
                'border': 'thin lightgrey dashed', 'padding': '6px 0px 0px 8px'}),

        #Body of page
        html.Div([

            #Funded Ratio Map
            html.Div([

                html.Br(),

                #Title for map
                html.Div(['State Public Pension Funded Ratio'],style={'textAlign':'center','fontSize':'25px'}),

                #Create map
                dcc.Graph(id='usa-ratio',
                            figure=px.choropleth(ratio_map, locations="state",
                                locationmode="USA-states", scope="usa",
                                color="adj_ratio",
                                hover_name="state",
                                #color='Blues',
                                color_continuous_scale='BuPu', #Currently not working - investigate later
                                animation_frame="fy",
                                range_color=(50,100), #Currently not working - investigate later
                                hover_data=["state"]),
                        hoverData={'points': [{'customdata': 'CO'}]})
            ],className='six columns'),

            #Tabs - right side of page
            html.Div([
                
                #Tabs
                html.Div([
                    dcc.Tabs(id='tabs-example',value='summary',children=[
                    dcc.Tab(label='Summary',value='summary'),
                    dcc.Tab(label='Data by State',value='state-summary'),
                    dcc.Tab(label='Data by Plan',value='plan-summary'),
                ],className='twelve columns'),

                html.Div(id='tabs-content-example')
                ],className='twelve columns')

            ],className='six columns'),

            html.Div(
                className='twelve_columns'
            )

        ],className='twelve columns'),

    ],className='twelve columns'),

    #Footers
    html.Div([
        html.Div(["Created by Jordan Bass 😻. Last edited: August 18, 2019."],
        style={'fontSize':'10px','textAlign':'center'}),

        html.Div(["Any opinions or analysis expressed are my own."],
        style={'fontSize':'10px','textAlign':'center'})
    ],className='twelve columns')

])

#####################################
#Tab Callbacks

#Tabs
@app.callback(Output('tabs-content-example','children'),[Input('tabs-example','value')])
def render_content(tab):
    if tab == 'summary':
        #Summary tab should just return markdown text for now
        return(
                html.Div([
                    dcc.Markdown(dedent("""
                    
                    ## How to Use

                    To use this tool, click on either the "Data by State" or "Data by Plan" tab.
                    Unless otherwise noted, data by state shows state averages for plans weighted by
                    plan size. 

                    On the map to the left, hover over a state to see the corresponding data in charts
                    in the tabs on the right.

                    More information to come.
                    
                    """))
                ])
            )

    elif tab=='state-summary':
        #Return state summary charts
        return(
                html.Br(),
                html.Div([
                        dcc.Dropdown(
                            id='chart-metric',
                            options=[{'label': i, 'value': i} for i in measures],
                            value='Historical Funded Ratio'
                        ),
                    ]), 

            html.Div([
                dcc.Graph(id='timeseries-ratio')
            ])
        )
    else:
        #Return plan-specific charts
        return(html.Div([
            html.Br(),
                html.Div([
                        dcc.Dropdown(
                            id='chart-metric',
                            options=[{'label': i, 'value': i} for i in measures],
                            value='Historical Funded Ratio'
                        ),
                    ]), 

            html.Div([
                dcc.Graph(id='timeseries-ratio')
            ]),

            html.Div([
                dcc.Markdown(dedent("""
                Dashed lines represent individual pension plans.
                
                Solid lines represent plan-weighted state average.
                """))
            ],style={'border': 'thin lightgrey solid','textAlign':'center'})
        ]))


#####################################
#Chart callbacks

@app.callback(
    Output('timeseries-ratio', 'figure'),
    [dash.dependencies.Input('usa-ratio', 'hoverData'), #selected state
    Input('chart-metric', 'value'), #selected chart metric from dropdown
    Input('tabs-example','value')]) #selected tab
def update_timeseries_ratio(hoverData,chart_metric,current_tab):
    
    #Selected state from hoverdata on map
    try:
        selected_state = hoverData['points'][0]['location']
    except: 
        selected_state = "CO"

    if current_tab == "state-summary": #if on data by state tab...
        if chart_metric == "Historical Funded Ratio": #Funded ratio chart
            subset = ratio_map[ratio_map['state']==selected_state] #subset data based on hoverdata state
            subset = subset[subset['fundedratio']>0]

            #Create line chart using plotly express
            fig = px.line(subset, x='fy', y='fundedratio',
            template='plotly_white',title="Historical Funded Ratio - "+selected_state,
            labels={'fy':'Fiscal Year','fundedratio':"Funded Ratio"})

        elif chart_metric == "Historical Annual Assumed Return": #Investment return chart
            subset = grouped_investassume[grouped_investassume['state']==selected_state] #subset data based on hoverdata state
            
            #Create line chart using plotly express
            fig = px.line(subset, x='fy', y='assumed_investment',
            template='plotly_white',title="Historical Assumed Investment Return - "+selected_state,
            labels={'fy':'Fiscal Year','assumed_investment':"Annual Assumed Investment"})
    else: #if on data by plan tab...
        if chart_metric == "Historical Funded Ratio": #Funded ratio chart
            subset = all_ratio[all_ratio['state']==selected_state] #subset data based on hoverdata state
            subset = subset[subset['fundedratio']>0]

            #Create line chart using plotly express
            fig = px.line(subset, x='fy', y='fundedratio',line_dash='state_avg',color='planname',
            template='plotly_white',title="Historical Funded Ratio - "+selected_state,
            labels={'fy':'Fiscal Year','fundedratio':"Funded Ratio",'planname':"Plan Name"})

            fig.update_layout(legend=dict(y=-.25,orientation="h"),showlegend=False)

        elif chart_metric == "Historical Annual Assumed Return": #Investment return chart
            subset = all_plans[all_plans['state']==selected_state] #subset data based on hoverdata state
            
            #Create line chart using plotly express
            fig = px.line(subset, x='fy', y='assumed_investment',line_dash='state_avg',color='planname',
            template='plotly_white',title="Historical Assumed Investment Return - "+selected_state,
            labels={'fy':'Fiscal Year','assumed_investment':"% Assumed Return",
            'planname':"Plan Name"})

            fig.update_layout(legend=dict(y=-.25,orientation="h"),showlegend=False)
    
    #return chart to layout
    return(fig)



# Run server
if __name__ == '__main__':
    app.run_server()
