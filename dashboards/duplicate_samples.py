import sys
import yaml
import os
import dash
import numpy as np
from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
pd.options.mode.chained_assignment = None

sys.path.append('../python/')
from dashboard_util import read_data, get_base_base_directory_path
from plotly_figure_parameters import dict_y_axis_parameters, dict_font_parameters, dict_x_axis_parameters_categorical


dash.register_page(__name__, path='/duplicate_samples/')

dict_parameters = yaml.safe_load(open("../parameters/july_2024_data_parameters.yaml", "r"))
pd_df_estimated_concentrations = read_data(dict_parameters)

pd_df_plate_data = pd.read_csv(
    open(
        os.path.join(
            get_base_base_directory_path(dict_parameters),
            dict_parameters["output directory"],
            dict_parameters["plate data with locations file name"]
        ),
        "rb"
    ),
    index_col=0,
)

def calculate_paired_intra_plate_cv(str_analyte, pd_group):
    if len(pd_group) != 2:
        return np.nan
    estimate_1, estimate_2 = pd_group[f"estimated concentration {str_analyte}"].values
    mean = (estimate_1 + estimate_2) / 2
    std_dev = np.sqrt((estimate_1 - mean)**2 + (estimate_2 - mean)**2)
    return std_dev / mean

def calculate_paired_intra_plate_rel_abs_diff(str_analyte, pd_group):
    if len(pd_group) != 2:
        return np.nan
    estimate_1, estimate_2 = pd_group[f"estimated concentration {str_analyte}"].values
    mean = (estimate_1 + estimate_2) / 2
    return np.abs(estimate_1 - estimate_2) / mean


def get_table_of_duplicate_qc_checks(function_check, str_check_name):
    list_pd_df_estimated_concentrations_checked_one_analyte = []
    for str_analyte in dict_parameters["list of analytes"]:
        pd_df_estimated_concentrations_checked_one_analyte = (
            pd_df_estimated_concentrations
            .groupby(["sample name annotations", "plate number"])
            .apply(lambda x: function_check(str_analyte, x), include_groups=False)
            .reset_index()
        )
        pd_df_estimated_concentrations_checked_one_analyte.columns = ["sample name annotations", "plate number"] + [
            f"{str_check_name} {str_analyte}"]
        list_pd_df_estimated_concentrations_checked_one_analyte.append(
            pd_df_estimated_concentrations_checked_one_analyte)

    pd_df_estimated_concentrations_checked = list_pd_df_estimated_concentrations_checked_one_analyte[0]
    for pd_df_estimated_concentrations_checked_one_analyte in list_pd_df_estimated_concentrations_checked_one_analyte[
                                                              1:]:
        pd_df_estimated_concentrations_checked = pd.merge(
            pd_df_estimated_concentrations_checked,
            pd_df_estimated_concentrations_checked_one_analyte,
            on=["sample name annotations", "plate number"],
            how="outer"
        )
    return pd_df_estimated_concentrations_checked

pd_df_CV = get_table_of_duplicate_qc_checks(
    calculate_paired_intra_plate_cv,
    "CV"
)
pd_df_rel_abs_diff = get_table_of_duplicate_qc_checks(
    calculate_paired_intra_plate_rel_abs_diff,
    "rel. abs. diff."
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

    dcc.Graph(id='scatter-plot-duplicates')
], style={'backgroundColor': 'white', 'padding': '20px'})


@callback(
    Output('scatter-plot-duplicates', 'figure'),
    Input('analyte-dropdown', 'value'),
    Input('plot-type-dropdown', 'value'),
    Input('statistic-dropdown', 'value'),
)
def update_graph(str_analyte, str_plot_type, str_statistic):
    if str_statistic == "CV":
        pd_df_data = pd_df_CV
    elif str_statistic == "rel. abs. diff.":
        pd_df_data = pd_df_rel_abs_diff

    str_column_name = f"{str_statistic} {str_analyte}"

    if str_plot_type == "box":
        fig = px.box(
            pd_df_data,
            x="plate number",
            y=str_column_name,
            hover_name="sample name annotations",
        )
    elif str_plot_type == "strip":
        fig = px.strip(
            pd_df_data,
            x="plate number",
            y=str_column_name,
            hover_name="sample name annotations",
        )
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
    )

    return fig