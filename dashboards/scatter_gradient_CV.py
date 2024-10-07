import sys
import yaml
import dash
from scipy import stats
import numpy as np
import plotly.graph_objects as go
from dash import dcc, html, callback
from dash.dependencies import Input, Output
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

dash.register_page(__name__, path='/scatter_gradient_CV/')

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
pd_df_data_cleaned = pd_df_data.dropna()

layout = html.Div([
    html.H1("Scatter plot of CV vs gradient or calibration interval"),

    html.Div([
        html.Label("Analyte:"),
        dcc.Dropdown(
            id='analyte-dropdown',
            options=[{'label': col, 'value': col} for col in dict_parameters["list of analytes"]],
            value=dict_parameters["list of analytes"][0]
        ),
    ], style={'width': '20%', 'display': 'inline-block'}),

    html.Div([
        html.Label("X axis:"),
        dcc.Dropdown(
            id='x-axis-dropdown',
            options=[
                {'label': 'max gradient', 'value': 'max gradient'},
                {'label': 'max cal interval', 'value': 'max cal interval'},
            ],
            value='max gradient',
        ),
    ], style={'width': '20%', 'display': 'inline-block'}),

    html.Div([
        dcc.Graph(id='scatter-plot-gradient-cv')
    ], style={'width': '80%'}),
], style={'backgroundColor': 'white', 'padding': '20px'})


@callback(
    Output('scatter-plot-gradient-cv', 'figure'),
    Input('analyte-dropdown', 'value'),
    Input('x-axis-dropdown', 'value'),
)
def update_graph(str_analyte, str_x_axis):
    fig = go.Figure()

    if str_x_axis == "max gradient":
        np_noise = np.zeros(len(pd_df_data))
    elif str_x_axis == "max cal interval":
        np_noise = np.random.uniform(-0.1, 0.1, len(pd_df_data))
    fig.add_trace(go.Scatter(
        x=pd_df_data[f"{str_x_axis} {str_analyte}"] + np_noise,
        y=pd_df_data[f"CV {str_analyte}"],
        mode='markers',
        hovertext=pd_df_data["sample name annotations"],
    ))

    slope, intercept, r_value, p_value, std_err = stats.linregress(
        pd_df_data_cleaned[f"{str_x_axis} {str_analyte}"],
        pd_df_data_cleaned[f"CV {str_analyte}"]
    )
    np_line_x = np.array([
        pd_df_data_cleaned[f"{str_x_axis} {str_analyte}"].min(),
        pd_df_data_cleaned[f"{str_x_axis} {str_analyte}"].max()
    ])
    np_line_y = slope * np_line_x + intercept

    fig.add_trace(go.Scatter(x=np_line_x, y=np_line_y, mode='lines'))

    textbox = f'Gradient: {slope:.2f}<br>p-value: {p_value:.4f}'
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.05, y=0.95,
        text=textbox,
        showarrow=False,
        font=dict(size=14),
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="black",
        borderwidth=1
    )
    # fig.update_traces(marker=dict(opacity=0.75))
    fig.update_layout(
        xaxis=dict_x_axis_parameters_categorical,
        yaxis=dict_y_axis_parameters,
        font=dict_font_parameters,
        xaxis_title=str_x_axis,
        yaxis_title="%CV",
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,
    )

    return fig