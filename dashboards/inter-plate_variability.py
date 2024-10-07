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

dash.register_page(__name__, path='/inter-plate_variability/')

dict_parameters = yaml.safe_load(open("../parameters/july_2024_data_parameters.yaml", "r"))
pd_df_estimated_concentrations = read_estimated_concentrations(dict_parameters)
pd_df_plate_data = read_plate_data_with_calibration_concentrations(dict_parameters)

list_sample_measurement_options = [
    {'label': 'QC-plasma concentration', 'value': 'QC-plasma concentration'},
    {'label': 'QC-1 concentration', 'value': 'QC-1 concentration'},
    {'label': 'QC-2 concentration', 'value': 'QC-2 concentration'},
]
for i in range(0, 8):
    list_sample_measurement_options.append(
        {'label': f'Std {i} fluorescent intensity', 'value': f'Std {i} fluorescent intensity'})


layout = html.Div([
    html.H1("Plots of quantities replicated across plates"),

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
        html.Label("Sample measurement:"),
        dcc.Dropdown(
            id='sample-measurement-dropdown',
            options=list_sample_measurement_options,
            value='QC-plasma concentration',
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
        dcc.Graph(id='scatter-plot-inter-plate')
    ], style={'width': '90%'}),
], style={'backgroundColor': 'white', 'padding': '20px'})


@callback(
    Output('scatter-plot-inter-plate', 'figure'),
    Input('analyte-dropdown', 'value'),
    Input('sample-measurement-dropdown', 'value'),
    Input('plot-type-dropdown', 'value'),
)
def update_graph(str_analyte, str_sample_measurement_type, str_plot_type):
    if "concentration" in str_sample_measurement_type:
        str_y_axis_title = "Concentration (pg/ml)"
        str_column_name = f"estimated concentration {str_analyte}"
        if str_sample_measurement_type == "QC-plasma concentration":
            pd_df_data = pd_df_estimated_concentrations[
                pd_df_estimated_concentrations["sample name annotations"].str.contains("QC-plasma")]
        elif str_sample_measurement_type == "QC-1 concentration":
            pd_df_data = pd_df_estimated_concentrations[
                pd_df_estimated_concentrations["sample name annotations"].str.contains("QC-1")]
        elif str_sample_measurement_type == "QC-2 concentration":
            pd_df_data = pd_df_estimated_concentrations[
                pd_df_estimated_concentrations["sample name annotations"].str.contains("QC-2")]
    else:
        str_y_axis_title = "Median fluorescent intensity"
        str_column_name = f"{str_analyte} Median"
        str_standard_name = " ".join(str_sample_measurement_type.split(" ")[:2])
        pd_df_data = pd_df_plate_data[pd_df_plate_data["sample name annotations"].str.contains(str_standard_name)]

    if str_plot_type == "box":
        fig = px.box(
            pd_df_data,
            x="plate number",
            y=str_column_name,
        )
    elif str_plot_type == "strip":
        fig = px.strip(
            pd_df_data,
            x="plate number",
            y=str_column_name,
            hover_name="sample name annotations",
        )
        fig.update_traces(marker=dict(opacity=0.75))

    fig.update_layout(
        xaxis=dict_x_axis_parameters_categorical,
        yaxis=dict_y_axis_parameters,
        font=dict_font_parameters,
        xaxis_title="plate number",
        yaxis_title=str_y_axis_title,
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    return fig