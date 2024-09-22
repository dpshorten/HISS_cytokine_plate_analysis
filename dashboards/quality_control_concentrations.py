import sys
import yaml
import os
import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
pd.options.mode.chained_assignment = None

sys.path.append('../python/')
from dashboard_util import read_data, get_base_base_directory_path


dash.register_page(__name__, path='/quality_control_concentrations/')

dict_parameters = yaml.safe_load(open("../parameters/july_2024_data_parameters.yaml", "r"))
pd_df_estimated_concentrations = read_data(dict_parameters)

LIST_ANALYTES_TO_CHECK = list(set(dict_parameters["list of analytes"]) - set(["IFN-gamma", "IP-10", "IL-17"]))

pd_df_quality_control_concentrations = pd.read_csv(
    open(
        os.path.join(
            get_base_base_directory_path(dict_parameters),
            dict_parameters["data directory"],
            dict_parameters["quality control concentrations file name"]
        ),
        "rb"
    )
)

pd_df_estimated_qc_concentrations = (
    pd_df_estimated_concentrations[
        pd_df_estimated_concentrations["sample name annotations"]
        .str.contains("QC-\d+", regex = True)
    ]
)

columns_to_keep = ["sample name annotations", "plate number"]
for str_analyte in LIST_ANALYTES_TO_CHECK:
    columns_to_keep.append(f"estimated concentration {str_analyte}")
pd_df_estimated_qc_concentrations = pd_df_estimated_qc_concentrations[columns_to_keep]

pd_df_estimated_qc_concentrations = pd_df_estimated_qc_concentrations.rename(
    columns = {f"estimated concentration {str_analyte}": str_analyte for str_analyte in LIST_ANALYTES_TO_CHECK}
)
pd_df_melted_estimated_qc_concentrations = pd_df_estimated_qc_concentrations.melt(
    id_vars = ["sample name annotations", "plate number"],
    var_name = "analyte",
    value_name = "concentration"
)
pd_df_melted_quality_control_concentrations = pd_df_quality_control_concentrations.melt(
    id_vars = ["QC name"],
    var_name = "analyte bound",
    value_name = "concentration"
)
pd_df_melted_quality_control_concentrations[["analyte", "bound"]] = (
    pd_df_melted_quality_control_concentrations["analyte bound"].str.split(" ", expand = True)
)
pd_df_melted_quality_control_concentrations = (
    pd_df_melted_quality_control_concentrations.drop(columns = ["analyte bound"])
)
pd_df_pivoted_quality_control_concentrations = pd_df_melted_quality_control_concentrations.pivot(
    index = ["QC name", "analyte"],
    columns = "bound",
    values = "concentration"
).reset_index().rename(columns = {"bound": "analyte", "QC name": "sample name annotations"})
pd_df_estimates_and_bounds = pd.merge(
    pd_df_melted_estimated_qc_concentrations,
    pd_df_pivoted_quality_control_concentrations,
    on = ["sample name annotations", "analyte"],
    how = "inner"
)

layout = html.Div([
    html.H1("Plots of estimated QC concentrations and bounds"),

    html.Div([
        html.Label("Plate:"),
        dcc.Dropdown(
            id='plate-dropdown',
            options=[
                {'label': plate_number, 'value': plate_number} for plate_number in
                dict_parameters["plate number to file associations"].keys()
            ],
            value=list(dict_parameters["plate number to file associations"].keys())[0]
        ),
    ], style={'width': '20%', 'display': 'inline-block'}),

    html.Div([
        html.Label("QC label:"),
        dcc.Dropdown(
            id='qc-label-dropdown',
            options=[
                {'label': 'QC-1', 'value': 'QC-1'},
                {'label': 'QC-2', 'value': 'QC-2'},
            ],
            value='QC-1',
        ),
    ], style={'width': '20%', 'display': 'inline-block'}),

    dcc.Graph(id='scatter-plot-qc')

], style={'backgroundColor': 'white', 'padding': '20px'})


@callback(
    Output('scatter-plot-qc', 'figure'),
    Input('plate-dropdown', 'value'),
    Input('qc-label-dropdown', 'value'),
)
def update_graph(int_plate_number, str_qc_label):

    pd_df_data_to_plot = pd_df_estimates_and_bounds[
        pd_df_estimates_and_bounds["plate number"] == int(int_plate_number)
        ]
    pd_df_data_to_plot = pd_df_data_to_plot[
        pd_df_data_to_plot["sample name annotations"].str.contains(str(str_qc_label))
    ]

    fig = go.Figure()

    for color, marker, size, column in zip(
            ['green', 'red', 'blue'],
            ['line-ew', 'line-ew', 'circle'],
            [20, 20, 5],
            ['low', 'high', 'concentration']
    ):
        fig.add_trace(
            go.Box(
                x=pd_df_data_to_plot["analyte"],
                y=pd_df_data_to_plot[column],
                name=column,
                boxpoints='all',
                pointpos=0,
                fillcolor='rgba(255,255,255,0)',
                line=dict(color='rgba(255,255,255,0)'),
                marker=dict(
                    symbol=marker, color=color, size=size,
                    line=dict(
                        color=color,
                        width=2,
                    ),
                ),
            )
        )

    fig.update_layout(
        xaxis=dict(
            title="Analyte",
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor='black',
            linewidth=2,
            ticks='outside',
            tickfont=dict(family='Arial', size=14, color='black'),
        ),
        yaxis=dict(
            title="Concentration (pg/ml)",
            showgrid=True,
            zeroline=True,
            showline=True,
            linecolor='black',
            linewidth=2,
            ticks='outside',
            tickfont=dict(family='Arial', size=14, color='black'),
        ),
        font=dict(
            family="Arial",
            size=16,
            color="black"
        ),

    )

    return fig
