import sys
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import dash_auth


import pandas as pd
pd.options.mode.chained_assignment = None

sys.path.append('../../python/')
from analysis_util import read_parameters_credentials_data, separate_concentrations_into_cohorts_and_clean

# Plotly Dash doesn't display error messages well, so we use logging
import logging
logging.basicConfig(level=logging.DEBUG, filename="dash_logs.log")

STR_URL_EXTENSION = "cohort_concentrations/"

def create_dash_app_object(dict_credentials, dict_pd_df_cohort_tables):

    dash_app_object = dash.Dash(
        __name__,
        url_base_pathname = dict_parameters["dashboard url base"] + STR_URL_EXTENSION
    )
    dash_auth_object = dash_auth.BasicAuth(
        dash_app_object,
        dict_credentials
    )

    dash_app_object.layout = html.Div([
        html.H1("Plots of estimated concentrations"),

        html.Div([
            html.Label("Cohort:"),
            dcc.Dropdown(
                id='cohort-dropdown',
                options=[{'label': col, 'value': col} for col in dict_parameters["list of cohort names"]],
                value=dict_parameters["list of cohort names"][0]
            ),
        ], style={'width': '20%', 'display': 'inline-block'}),

        html.Div([
            html.Label("Plot type:"),
            dcc.Dropdown(
                id='plot-type-dropdown',
                options=[
                    {'label': 'box', 'value': 'box'},
                    {'label': 'strip', 'value': 'strip'},
                ],
                value='box',
            ),
        ], style={'width': '20%', 'display': 'inline-block'}),

        html.Div([
            html.Label("Data type:"),
            dcc.Dropdown(
                id='data-type-dropdown',
                options=[
                    {'label': 'raw estimates', 'value': 'raw estimates'},
                    {'label': 'differences', 'value': 'differences'},
                ],
                value='raw estimates',
            ),
        ], style={'width': '20%', 'display': 'inline-block'}),

        html.Div([
            html.Label("Analyte:"),
            dcc.Dropdown(
                id='analyte-dropdown',
                options=[{'label': col, 'value': col} for col in dict_parameters["list of analytes"]],
                value=dict_parameters["list of analytes"][0]
            ),
        ], style={'width': '20%', 'display': 'inline-block'}),

        dcc.Graph(id='scatter-plot')
    ], style={'backgroundColor': 'white', 'padding': '20px'})


    @dash_app_object.callback(
        Output('scatter-plot', 'figure'),
        Input('cohort-dropdown', 'value'),
        Input('analyte-dropdown', 'value'),
        Input('data-type-dropdown', 'value'),
        Input('plot-type-dropdown', 'value'),
    )
    def update_graph(str_cohort_name, str_analyte, str_data_type, str_plot_type):
        if str_data_type == "raw estimates":
            str_column_name = dict_parameters["column name prefix for estimated concentrations"] + str_analyte
        elif str_data_type == "differences":
            str_column_name = str_analyte + " diff"

        if str_plot_type == "box":
            fig = px.box(
                dict_pd_df_cohort_tables[str_cohort_name],
                x="time code",
                y=str_column_name,
            )
        elif str_plot_type == "strip":
            fig = px.strip(
                dict_pd_df_cohort_tables[str_cohort_name],
                x="time code",
                y=str_column_name,
                hover_name="patient number",
            )
            fig.update_traces(marker=dict(opacity=0.75))

        if str_data_type == "raw estimates":
            str_y_label = "concentration"
        elif str_data_type == "differences":
            str_y_label = "diff. in concentration"
        fig.update_layout(
            #plot_bgcolor='white',
            #paper_bgcolor='white',
            xaxis_title="time",
            # xaxis=dict(
            #     tickmode='array',
            #     tickvals=['A', 'B', 'C', 'D', 'E'],
            #     ticktext=['minus 1wk', 'minus 1hr', 'plus 3hr', 'plus 7hr', 'plus 25hr'],
            # ),
            yaxis_title=str_y_label,
            font=dict(
                family="Arial",
                size=16,
                color="black"
            )
        )
        return fig

    return dash_app_object

if __name__ == '__main__':

    # Read the parameters, credentials and data
    dict_parameters, dict_credentials, pd_df_estimated_concentrations = read_parameters_credentials_data(sys.argv[1])
    # Process the data
    dict_pd_df_cohort_tables = separate_concentrations_into_cohorts_and_clean(
        dict_parameters,
        pd_df_estimated_concentrations
    )
    # Create the Dash app object
    dash_app_object = create_dash_app_object(dict_credentials, dict_pd_df_cohort_tables)

    dash_app_object.run(host='0.0.0.0', port=9999)