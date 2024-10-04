import sys
import yaml
import os
import numpy as np
import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
pd.options.mode.chained_assignment = None

sys.path.append('../python/')
from dashboard_notebook_util import read_estimated_concentrations, get_base_base_directory_path
import plate_util
import calibration_curves
from plotly_figure_parameters import dict_y_axis_parameters, dict_font_parameters, dict_x_axis_parameters_continuous

DICT_INCLUSION_COLOURS = {
    "included": "blue",
    "excluded": "red"
}

dash.register_page(__name__, path='/calibration_curves/')

dict_parameters = yaml.safe_load(open("../parameters/july_2024_data_parameters.yaml", "r"))
pd_df_estimated_concentrations = read_estimated_concentrations(dict_parameters)

pd_df_plate_data_with_calibration_concentrations = pd.read_csv(
        open(
            os.path.join(
                get_base_base_directory_path(dict_parameters),
                dict_parameters["output directory"],
                dict_parameters["plate data with locations and calibration concentrations file name"]
            ),
            "rb"
        ),
    index_col = 0,
)
pd_df_calibration_concentrations = plate_util.read_and_clean_calibration_concentrations(
    dict_parameters,
    get_base_base_directory_path(dict_parameters)
)
dict_fitted_calibration_curves = yaml.safe_load(
    open(
            os.path.join(
                get_base_base_directory_path(dict_parameters),
                dict_parameters["output directory"],
                dict_parameters["fitted calibration curves file name"]
            ),
            "r"
        )
)

layout = html.Div([
    html.H1("Calibration Curve Inspection Plots"),

    html.Div([
        html.Label("Plate:"),
        dcc.Dropdown(
            id='plate-number-dropdown-calibration',
            options=[
                {'label': col, 'value': col}
                for col in dict_parameters["plate number to file associations"].keys()
            ],
            value=list(dict_parameters["plate number to file associations"].keys())[0]
        ),
    ], style={'width': '20%', 'display': 'inline-block'}),

    html.Div([
        html.Label("Sample:"),
        dcc.Dropdown(
            id='sample-dropdown-calibration',
        ),
    ], style={'width': '20%', 'display': 'inline-block'}),

    html.Div([
        html.Label("Analyte:"),
        dcc.Dropdown(
            id='analyte-dropdown-calibration',
            options=[{'label': col, 'value': col} for col in dict_parameters["list of analytes"]],
            value=dict_parameters["list of analytes"][0]
        ),
    ], style={'width': '20%', 'display': 'inline-block'}),

    dcc.Graph(id='scatter-plot-calibration')
], style={'backgroundColor': 'white', 'padding': '20px'})


@callback(
    Output('sample-dropdown-calibration', 'options'),
    Input('plate-number-dropdown-calibration', 'value'),
)
def set_plate_number_options(selected_plate_number):
    pd_df_subset = (
        pd_df_estimated_concentrations[
            pd_df_estimated_concentrations["plate number"] == selected_plate_number
            ]
    )

    return [
        {'label': sample_name, 'value': sample_name}
        for sample_name in pd_df_subset["sample name annotations"].unique()
    ]


@callback(
    Output('scatter-plot-calibration', 'figure'),
    Input('plate-number-dropdown-calibration', 'value'),
    Input('analyte-dropdown-calibration', 'value'),
    Input('sample-dropdown-calibration', 'value'),
)
def update_graph(plate_number, str_analyte, str_sample_name):
    dict_fit_results = (
        dict_fitted_calibration_curves["calibration curves by plate"][plate_number][str_analyte]
    )
    pd_df_one_plates_data = (
        pd_df_plate_data_with_calibration_concentrations[
            pd_df_plate_data_with_calibration_concentrations["plate number"] == plate_number
            ]
    )
    pd_df_one_plates_data = pd_df_one_plates_data[pd_df_one_plates_data["sample name annotations"].str.contains("Std")]
    # pd_df_one_plates_data = pd_df_one_plates_data[~pd_df_one_plates_data["sample name annotations"].str.contains("Std 0")]

    dict_LOO_results = dict_fit_results["dict LOO results"]
    list_LOO_plate_rows = []
    list_LOO_plate_columns = []
    list_LOO_excluded = []
    for str_LOO_sample_name in dict_LOO_results.keys():
        list_LOO_plate_rows.append(dict_LOO_results[str_LOO_sample_name]["plate row"])
        list_LOO_plate_columns.append(dict_LOO_results[str_LOO_sample_name]["plate column"])
        list_LOO_excluded.append("excluded")
    pd_df_LOO_results = pd.DataFrame(
        {
            "plate row": list_LOO_plate_rows,
            "plate column": list_LOO_plate_columns,
            "inclusion": list_LOO_excluded,
        }
    )
    pd_df_one_plates_data = pd_df_one_plates_data.merge(
        pd_df_LOO_results,
        how="left",
        on=["plate row", "plate column"],
    )
    pd_df_one_plates_data = pd_df_one_plates_data.fillna({"inclusion": "included"})


    np_curve_plot_points = np.logspace(
        0,
        np.log(max(pd_df_one_plates_data[str_analyte + " Expected"])) / np.log(10),
        1000,
        base=10,
        endpoint=False,
    )

    fig = go.Figure()
    for str_inclusion, pd_df_group in pd_df_one_plates_data.groupby('inclusion'):
        fig.add_traces(
            go.Scatter(
                x=pd_df_group[str_analyte + " Expected"],
                y=pd_df_group[str_analyte + " " + dict_parameters["quantity for estimation"]],
                error_y={
                    'type': 'data',
                    'array': (
                            pd_df_group[str_analyte + " Std Dev"] /
                            np.sqrt(pd_df_group[str_analyte + " Count"])
                    ),
                    'visible': True,
                    #'color' : list(pd_df_group["inclusion"].map(DICT_INCLUSION_COLOURS).values),
                },
                mode='markers',
                name=str_inclusion + " standard",
                marker=dict(
                    size=7,
                    color=DICT_INCLUSION_COLOURS[str_inclusion],
                    #colorscale='Viridis',
                    #showscale=True
                )

            )
        )

    fig.add_traces(
        go.Scatter(
            x=np_curve_plot_points,
            y=calibration_curves.get_calibration_curve_function(dict_parameters)(
                np_curve_plot_points,
                *dict_fit_results["fitted parameters"],
            ),
            mode='lines',
            name='calibration curve',
            line={
                "width": 2,
                "color": "darkgreen",
            },

        )
    )

    if str_sample_name:
        pd_df_estimations_for_selection = (
            pd_df_estimated_concentrations[
                (pd_df_estimated_concentrations["plate number"] == plate_number) &
                (pd_df_estimated_concentrations["sample name annotations"] == str_sample_name)
                ]
        )
        fig.add_traces(
            go.Scatter(
                x=pd_df_estimations_for_selection[
                    dict_parameters["column name prefix for estimated concentrations"] + str_analyte
                    ],
                y=pd_df_estimations_for_selection[str_analyte + " " + dict_parameters["quantity for estimation"]],
                error_y={
                    'type': 'data',
                    'array': (
                            pd_df_estimations_for_selection[str_analyte + " Std Dev"] /
                            np.sqrt(pd_df_estimations_for_selection[str_analyte + " Count"])
                    ),
                    'visible': True
                },
                mode='markers',
                name='estimated concentrations',
                marker={'size': 7, 'color': 'black'},
            )
        )
    fig.update_layout(
        xaxis_type="log",
        xaxis_title="concentration (pg/ml)",
        yaxis_title="fluorescent intensity",
        xaxis=dict_x_axis_parameters_continuous,
        yaxis=dict_y_axis_parameters,
        font=dict_font_parameters,
    )
    return fig