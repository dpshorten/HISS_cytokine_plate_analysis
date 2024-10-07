import sys
import yaml
import os
import dash
import plotly.graph_objects as go
import numpy as np
from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
pd.options.mode.chained_assignment = None

sys.path.append('../python/')
from dashboard_notebook_util import (
    read_estimated_concentrations,
    read_plate_data_with_calibration_concentrations,
    read_quality_control_concentrations,
    get_base_base_directory_path
)
from plotly_figure_parameters import dict_y_axis_parameters, dict_font_parameters, dict_x_axis_parameters_categorical
from analysis_util import get_table_with_all_duplicate_qc_checks
import plate_util

dash.register_page(__name__, path='/intra-plate_variability/')

dict_parameters = yaml.safe_load(open("../parameters/july_2024_data_parameters.yaml", "r"))
pd_df_estimated_concentrations = read_estimated_concentrations(dict_parameters)
pd_df_plate_data = read_plate_data_with_calibration_concentrations(dict_parameters)
pd_df_calibration_concentrations = plate_util.read_and_clean_calibration_concentrations(
    dict_parameters,
    str_base_directory_path=get_base_base_directory_path(dict_parameters)
)
pd_df_data = get_table_with_all_duplicate_qc_checks(
    dict_parameters,
    pd_df_estimated_concentrations,
    pd_df_calibration_concentrations
)

layout = html.Div([
    html.H1("Plots of statistics comparing duplicate samples"),

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
        html.Label("Analyte:"),
        dcc.Dropdown(
            id='analyte-dropdown',
            options=[{'label': col, 'value': col} for col in dict_parameters["list of analytes"]],
            value=dict_parameters["list of analytes"][0]
        ),
    ], style={'width': '20%', 'display': 'inline-block'}),

    html.Div([
        html.Label("Statistic:"),
        dcc.Dropdown(
            id='statistic-dropdown',
            options=[
                {'label': 'CV', 'value': 'CV'},
                {'label': 'rel. abs. diff.', 'value': 'rel. abs. diff.'},
            ],
            value='CV',
        ),
    ], style={'width': '20%', 'display': 'inline-block'}),

    html.Div([
        html.Label("Strip colour:"),
        dcc.Dropdown(
            id='strip-colour-dropdown',
            options=[
                {'label': 'max gradient', 'value': 'max gradient'},
                {'label': 'max cal interval', 'value': 'max cal interval'},
            ],
            value='max gradient',
        ),
    ], style={'width': '20%', 'display': 'inline-block'}),

    html.Div([
        dcc.Graph(id='scatter-plot-duplicates')
    ], style={'width': '80%'}),
], style={'backgroundColor': 'white', 'padding': '20px'})


@callback(
    Output('scatter-plot-duplicates', 'figure'),
    Input('analyte-dropdown', 'value'),
    Input('plot-type-dropdown', 'value'),
    Input('statistic-dropdown', 'value'),
    Input('strip-colour-dropdown', 'value'),
)
def update_graph(str_analyte, str_plot_type, str_statistic, str_strip_colour):
    str_column_name = f"{str_statistic} {str_analyte}"

    if str_plot_type == "box":
        fig = px.box(
            pd_df_data,
            x="plate number",
            y=str_column_name,
            hover_name="sample name annotations",
        )
    elif str_plot_type == "strip":

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=pd_df_data["plate number"] + np.random.uniform(-0.1, 0.1, len(pd_df_data)),
            y=pd_df_data[str_column_name],
            mode='markers',
            marker=dict(
                size=8,
                color=pd_df_data[str_strip_colour + " " + str_analyte],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="\n".join(str_strip_colour.split(" ")), titlefont=dict(size=14)),

            ),
            hovertext=pd_df_data["sample name annotations"],
        ))
        fig.update_traces(marker=dict(opacity=0.75))
    if str_statistic == "CV":
        str_y_axis_title = "%CV"
    else:
        str_y_axis_title = str_statistic
    fig.update_layout(
        xaxis=dict_x_axis_parameters_categorical,
        yaxis=dict_y_axis_parameters,
        font=dict_font_parameters,
        xaxis_title="Plate",
        yaxis_title=str_y_axis_title,
        plot_bgcolor='white',
        paper_bgcolor='white',
    )

    return fig