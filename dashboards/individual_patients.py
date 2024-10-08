import sys
import yaml
import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
pd.options.mode.chained_assignment = None

sys.path.append('../python/')
from analysis_util import separate_concentrations_into_cohorts_and_clean
from dashboard_notebook_util import read_estimated_concentrations
from plotly_figure_parameters import dict_y_axis_parameters, dict_font_parameters, dict_x_axis_parameters_continuous


dash.register_page(__name__, path='/individual_patients/')

dict_parameters = yaml.safe_load(open("../parameters/july_2024_data_parameters.yaml", "r"))
pd_df_estimated_concentrations = read_estimated_concentrations(dict_parameters)
dict_pd_df_cohort_tables = separate_concentrations_into_cohorts_and_clean(
    dict_parameters,
    pd_df_estimated_concentrations
)


list_patient_ids_melbourne = list(dict_pd_df_cohort_tables["Melbourne"]["patient number"].unique())
list_patient_ids_adelaide = list(dict_pd_df_cohort_tables["Adelaide"]["patient number"].unique())
list_patient_id_dropdown_dicts = [
    {'label': str_patient_id, 'value': str_patient_id} for str_patient_id in
    list_patient_ids_adelaide + list_patient_ids_melbourne
]

# Define the layout
layout = html.Div([
    html.H1("Line plots by patient number"),

    html.Div([
        html.Label("Patient number:"),
        dcc.Dropdown(
            id='patient-number-dropdown',
            options=list_patient_id_dropdown_dicts,
            value=list_patient_id_dropdown_dicts[0]["value"],
        ),
    ], style={'width': '20%', 'display': 'inline-block'}),

    html.Div([
        html.Label("Data type:"),
        dcc.Dropdown(
            id='data-type-dropdown',
            options=[
                {'label': 'raw estimates', 'value': 'raw estimates'},
                {'label': 'normalised raw estimates', 'value': 'normalised raw estimates'},
                {'label': 'differences', 'value': 'differences'},
            ],
            value='raw estimates',
        ),
    ], style={'width': '20%', 'display': 'inline-block'}),

    dcc.Graph(id='line-plot')
], style={'backgroundColor': 'white', 'padding': '20px'})
@callback(
    Output('line-plot', 'figure'),
    Input('patient-number-dropdown', 'value'),
    Input('data-type-dropdown', 'value'),
)
def update_graph(str_patient_number, str_data_type):
    fig = go.Figure()
    if str_patient_number in list_patient_ids_melbourne:
        pd_df_patients_data = (
            dict_pd_df_cohort_tables["Melbourne"][
                dict_pd_df_cohort_tables["Melbourne"]["patient number"] == str_patient_number]
        )
    elif str_patient_number in list_patient_ids_adelaide:
        pd_df_patients_data = (
            dict_pd_df_cohort_tables["Adelaide"][
                dict_pd_df_cohort_tables["Adelaide"]["patient number"] == str_patient_number]
        )

    for str_analyte in ["IP-10", "IFN-gamma", "IL-6", "TNF-a"]:

        if str_data_type in ["raw estimates", "normalised raw estimates"]:
            str_column_name = dict_parameters["column name prefix for estimated concentrations"] + str_analyte
        elif str_data_type == "differences":
            str_column_name = str_analyte + " diff"
        pd_series_y = pd_df_patients_data[str_column_name]
        if str_data_type == "normalised raw estimates":
            pd_series_y = (pd_series_y - pd_series_y.mean()) / (pd_series_y.max() - pd_series_y.min())
        fig.add_trace(go.Scatter(x=pd_df_patients_data["time int"], y=pd_series_y, mode='lines', name=str_analyte))

    if str_data_type == "raw estimates":
        str_y_label = "concentration (pg/ml)"
    if str_data_type == "normalised raw estimates":
        str_y_label = "normalised concentration"
    elif str_data_type == "differences":
        str_y_label = "diff. in concentration (pg/ml)"

    if str_patient_number in list_patient_ids_melbourne:
        list_x_tickvals=[1, 2, 3, 4, 5]
        list_x_ticktext=['minus 1wk', 'minus 1hr', 'plus 3hr', 'plus 7hr', 'plus 25hr']
    elif str_patient_number in list_patient_ids_adelaide:
        list_x_tickvals=[1, 2, 3, 4, 5, 6, 7]
        list_x_ticktext=['minus 1hr', 'plus 15min', 'plus 30min', 'plus 1hr', 'plus 2hr', 'plus 4hr', 'plus 8hr']

    fig.update_layout(
        xaxis=dict_x_axis_parameters_continuous,
        yaxis=dict_y_axis_parameters,
        xaxis_title="time",
        yaxis_title=str_y_label,
        xaxis_tickvals=list_x_tickvals,
        xaxis_ticktext=list_x_ticktext,
        font=dict_font_parameters,
    )
    return fig



