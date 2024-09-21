import sys
import os
import yaml
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import dash_auth


import pandas as pd
pd.options.mode.chained_assignment = None

sys.path.append('../python/')

# Plotly Dash doesn't display error messages well, so we use logging
import logging
logging.basicConfig(level=logging.DEBUG, filename="dash_logs.log")

def read_parameters_credentials_data():

    dict_parameters = yaml.safe_load(open("../parameters/july_2024_data_parameters.yaml", "r"))

    pd_df_credentials = pd.read_csv(
        open(
            dict_parameters["dashboard credentials file location"],
            "rb"
        )
    )
    dict_credentials = dict(zip(pd_df_credentials['username'], pd_df_credentials['password']))

    pd_df_estimated_concentrations = pd.read_csv(
        open(
            os.path.join(
                dict_parameters["output directory path"],
                dict_parameters["estimated concentrations file name"]
            ),
            "rb"
        )
    )

    return dict_parameters, dict_credentials, pd_df_estimated_concentrations

def process_data_for_individual_patient_plots(dict_parameters, pd_df_estimated_concentrations):

    dict_pd_df_cohort_tables = {}
    dict_pd_df_cohort_tables["Melbourne"] = pd_df_estimated_concentrations[
        pd_df_estimated_concentrations["sample name annotations"].str.contains('\d{3,4}[ _][A-Za-z]', regex=True)
    ]
    dict_pd_df_cohort_tables["Adelaide"] = pd_df_estimated_concentrations[
        pd_df_estimated_concentrations["sample name annotations"].str.contains('\d{4}A_.*', regex=True)
    ]

    list_columns_to_keep = ["sample name annotations"]
    for str_analyte in dict_parameters["list of analytes"]:
            list_columns_to_keep.append(dict_parameters["column name prefix for estimated concentrations"] + str_analyte)
    for cohort_name in dict_parameters["list of cohort names"]:
        dict_pd_df_cohort_tables[cohort_name] = dict_pd_df_cohort_tables[cohort_name][list_columns_to_keep]
    dict_pd_df_cohort_tables["Adelaide"]

    for cohort_name in dict_parameters["list of cohort names"]:
        dict_pd_df_cohort_tables[cohort_name] = dict_pd_df_cohort_tables[cohort_name].groupby("sample name annotations").mean().reset_index()

    dict_pd_df_cohort_tables["Adelaide"]["sample name annotations"] = (
        dict_pd_df_cohort_tables["Adelaide"]["sample name annotations"].str.replace("_D2", "-D2")
    )

    for cohort_name in dict_parameters["list of cohort names"]:
        dict_pd_df_cohort_tables[cohort_name][["patient number", "time code"]] = (
            dict_pd_df_cohort_tables[cohort_name]["sample name annotations"]
            .str.strip()
            .str.split(r"[_ ]", expand = True)
        )
        dict_pd_df_cohort_tables[cohort_name] = dict_pd_df_cohort_tables[cohort_name].drop(columns = ["sample name annotations"])

    dict_pd_df_cohort_tables["Melbourne"] = (
        dict_pd_df_cohort_tables["Melbourne"][
            dict_pd_df_cohort_tables["Melbourne"].groupby("patient number")["patient number"].transform('count') >= 5
        ]
    )
    dict_pd_df_cohort_tables["Melbourne"] = dict_pd_df_cohort_tables["Melbourne"].reset_index(drop = True)

    dict_melbourne_time_code_mapping = {
        'A': 1,
        'B': 2,
        'C': 3,
        'D': 4,
        'E': 5,
    }
    dict_pd_df_cohort_tables["Melbourne"]["time int"] = (
        dict_pd_df_cohort_tables["Melbourne"]["time code"].map(dict_melbourne_time_code_mapping)
    )
    dict_adelaide_time_code_mapping = {
        'Pre-1hr': 1,
        '-1hr': 1,
        '15min': 2,
        '0.5hr': 3,
        '1hr': 4,
        '2hr': 5,
        '4hr': 6,
        '8hr': 7,
    }
    dict_pd_df_cohort_tables["Adelaide"]["time int"] = (
        dict_pd_df_cohort_tables["Adelaide"]["time code"].map(dict_adelaide_time_code_mapping)
    )

    for cohort_name in dict_parameters["list of cohort names"]:
        dict_pd_df_cohort_tables[cohort_name] = dict_pd_df_cohort_tables[cohort_name].sort_values(
            by=["patient number", "time int"]).reset_index()

    list_first_columns = [
        "patient number", "time code", "time int"
    ]
    for cohort_name in dict_parameters["list of cohort names"]:
        dict_pd_df_cohort_tables[cohort_name] = (
            dict_pd_df_cohort_tables[cohort_name][
                list_first_columns +
                [column_name for column_name in dict_pd_df_cohort_tables[cohort_name].columns if
                 column_name not in list_first_columns]
                ]
        )

    dict_pd_df_cohort_tables["Adelaide"].groupby("patient number").apply(
        lambda x: x["estimated concentration " + "IFN-gamma"]
                              - x[x["time int"] == 1]["estimated concentration " + "IFN-gamma"].iloc[0],
                    include_groups = False,
    )

    for str_cohort_name, int_base_time_code in zip(dict_parameters["list of cohort names"], [2, 1]):
        for str_analyte in dict_parameters["list of analytes"]:
            dict_pd_df_cohort_tables[str_cohort_name][str_analyte + " diff"] = (
                dict_pd_df_cohort_tables[str_cohort_name].groupby("patient number").apply(
                    lambda x: x["estimated concentration " + str_analyte]
                              - x[x["time int"] == int_base_time_code]["estimated concentration " + str_analyte].iloc[0],
                    include_groups = False,
                )
            ).reset_index(drop = True)

    return dict_pd_df_cohort_tables

def create_dash_app_object(dict_credentials, dict_pd_df_cohort_tables):

    dash_app_object_lines = dash.Dash(__name__, url_base_pathname = "/individual_patients/")
    dash_auth_object = dash_auth.BasicAuth(
        dash_app_object_lines,
        dict_credentials
    )

    list_patient_ids_melbourne = list(dict_pd_df_cohort_tables["Melbourne"]["patient number"].unique())
    list_patient_ids_adelaide = list(dict_pd_df_cohort_tables["Adelaide"]["patient number"].unique())
    list_patient_id_dropdown_dicts = [
        {'label': str_patient_id, 'value': str_patient_id} for str_patient_id in
        list_patient_ids_adelaide + list_patient_ids_melbourne
    ]

    # Define the layout
    dash_app_object_lines.layout = html.Div([
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
    @dash_app_object_lines.callback(
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
            dict_x_ticks = dict(
                tickmode='array',
                tickvals=[1, 2, 3, 4, 5],
                ticktext=['minus 1wk', 'minus 1hr', 'plus 3hr', 'plus 7hr', 'plus 25hr'],
            )
        elif str_patient_number in list_patient_ids_adelaide:
            dict_x_ticks = dict(
                tickmode='array',
                tickvals=[1, 2, 3, 4, 5, 6, 7],
                ticktext=['minus 1hr', 'plus 15min', 'plus 30min', 'plus 1hr', 'plus 2hr', 'plus 4hr', 'plus 8hr'],
            )

        fig.update_layout(
            xaxis_title="time",
            xaxis=dict_x_ticks,
            yaxis=dict(
                title=str_y_label,
                showgrid=True,
                zeroline=True,
                showline=True,
                linecolor='black',
                linewidth=2,
            ),
            font=dict(
                family="Arial",
                size=16,
                color="black"
            )
        )
        return fig

    return dash_app_object_lines

if __name__ == '__main__':

    # Read the parameters, credentials and data
    dict_parameters, dict_credentials, pd_df_estimated_concentrations = read_parameters_credentials_data()
    # Process the data
    dict_pd_df_cohort_tables = process_data_for_individual_patient_plots(
        dict_parameters,
        pd_df_estimated_concentrations
    )
    # Create the Dash app object
    dash_app_object_lines = create_dash_app_object(dict_credentials, dict_pd_df_cohort_tables)

    dash_app_object_lines.run(host='0.0.0.0', port=9999)