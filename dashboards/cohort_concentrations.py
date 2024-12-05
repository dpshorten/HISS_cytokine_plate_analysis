import sys
import yaml
import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
pd.options.mode.chained_assignment = None

sys.path.append('../python/')
from analysis_util import separate_concentrations_into_cohorts_and_clean, add_concentration_diffs_to_one_cohort_table
from dashboard_notebook_util import read_estimated_concentrations
from plotly_figure_parameters import dict_y_axis_parameters, dict_font_parameters, dict_x_axis_parameters_categorical

dash.register_page(__name__, path='/cohort_concentrations/')

dict_parameters = yaml.safe_load(open("../parameters/july_2024_data_parameters.yaml", "r"))
pd_df_estimated_concentrations = read_estimated_concentrations(dict_parameters)
dict_pd_df_cohort_tables = separate_concentrations_into_cohorts_and_clean(
    dict_parameters,
    pd_df_estimated_concentrations
)

pd_df_adelaide = dict_pd_df_cohort_tables["Adelaide"].copy()
pd_df_adelaide = pd_df_adelaide.loc[:, ~pd_df_adelaide.columns.str.endswith("diff")]
pd_df_adelaide["day"] = 1
pd_df_adelaide["patient number"] = pd_df_adelaide["patient number"].astype(str)
pd_df_adelaide.loc[pd_df_adelaide["patient number"].str.endswith("D2"), "day"] = 2
pd_df_adelaide["patient number"] = (
    pd_df_adelaide["patient number"].str.replace('-D2', '')
)
pd_df_adelaide_day_one = (
    pd_df_adelaide[pd_df_adelaide["day"] == 1].set_index(["patient number", "time code", "time int"], drop=True)
)
pd_df_adelaide_day_two = (
    pd_df_adelaide[pd_df_adelaide["day"] == 2].set_index(["patient number", "time code", "time int"], drop=True)
)

pd_df_adelaide_differences = (pd_df_adelaide_day_two - pd_df_adelaide_day_one).abs().reset_index()
add_concentration_diffs_to_one_cohort_table(dict_parameters, pd_df_adelaide_differences, 1)
print(pd_df_adelaide_differences)


layout = html.Div([
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

@callback(
    Output('data-type-dropdown', 'options'),
    Input('cohort-dropdown', 'value'),
)
def set_data_type_options(selected_cohort):

    if selected_cohort == "Melbourne":
        return [
            {'label': 'raw estimates', 'value': 'raw estimates'},
            {'label': 'differences', 'value': 'differences'},
        ]

    elif selected_cohort == "Adelaide":
        return [
            {'label': 'raw estimates', 'value': 'raw estimates'},
            {'label': 'differences', 'value': 'differences'},
            {'label': 'treatment absolute differences', 'value': 'treatment absolute differences'},
            {'label': 'treatment abs diffs with baseline diff', 'value': 'treatment abs diffs with baseline diff'},
        ]

@callback(
    Output('scatter-plot', 'figure'),
    Input('cohort-dropdown', 'value'),
    Input('analyte-dropdown', 'value'),
    Input('data-type-dropdown', 'value'),
    Input('plot-type-dropdown', 'value'),
)
def update_graph(str_cohort_name, str_analyte, str_data_type, str_plot_type):

    if str_data_type == "raw estimates":
        str_column_name = dict_parameters["column name prefix for estimated concentrations"] + str_analyte
        pd_df_data = dict_pd_df_cohort_tables[str_cohort_name]
    elif str_data_type == "differences":
        str_column_name = str_analyte + " diff"
        pd_df_data = dict_pd_df_cohort_tables[str_cohort_name]
    elif str_data_type == "treatment absolute differences":
        str_column_name = dict_parameters["column name prefix for estimated concentrations"] + str_analyte
        pd_df_data = pd_df_adelaide_differences
    elif str_data_type == "treatment abs diffs with baseline diff":
        str_column_name = str_analyte + " diff"
        pd_df_data = pd_df_adelaide_differences

    if str_plot_type == "box":
        fig = px.box(
            pd_df_data,
            x="time int",
            y=str_column_name,
        )
    elif str_plot_type == "strip":
        fig = px.strip(
            pd_df_data,
            x="time int",
            y=str_column_name,
            hover_name="patient number",
        )
        fig.update_traces(marker=dict(opacity=0.75))

    if str_data_type == "raw estimates":
        str_y_label = "concentration (pg/ml)"
    elif str_data_type in ["differences", "treatment absolute differences", "treatment abs diffs with baseline diff"]:
        str_y_label = "diff. in concentration (pg/ml)"

    if str_cohort_name == "Melbourne":
        list_x_tickvals=[1, 2, 3, 4, 5]
        list_x_ticktext=['minus 1wk', 'minus 1hr', 'plus 3hr', 'plus 7hr', 'plus 25hr']
    elif str_cohort_name == "Adelaide":
        list_x_tickvals=[1, 2, 3, 4, 5, 6, 7]
        list_x_ticktext=['minus 1hr', 'plus 15min', 'plus 30min', 'plus 1hr', 'plus 2hr', 'plus 4hr', 'plus 8hr']

    fig.update_layout(
        xaxis=dict_x_axis_parameters_categorical,
        yaxis=dict_y_axis_parameters,
        font=dict_font_parameters,
        yaxis_title=str_y_label,
        xaxis_title="time",
        xaxis_tickvals=list_x_tickvals,
        xaxis_ticktext=list_x_ticktext,
    )
    return fig