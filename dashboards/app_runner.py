import dash
import dash_auth
from dash import Dash, html, dcc
import pandas as pd
import os
import yaml

dict_parameters = yaml.safe_load(open("../parameters/july_2024_data_parameters.yaml", "r"))
pd_df_credentials = pd.read_csv(
        open(
            os.path.join(
                dict_parameters["base directory path"],
                dict_parameters["dashboard credentials file path"]
            ),
            "rb"
        )
    )
dict_credentials = dict(zip(pd_df_credentials['username'], pd_df_credentials['password']))

dash_app_object = Dash(
    __name__,
    use_pages=True,
    pages_folder=".",
)
dash_auth_object = dash_auth.BasicAuth(
    dash_app_object,
    dict_credentials
)

dash_app_object.layout = html.Div([
    html.Div([
        html.Div(
            dcc.Link(f"{page['name']}", href=page["relative_path"])
        ) for page in list(dash.page_registry.values())[1:]
    ]),
    dash.page_container
])

if __name__ == '__main__':
    dash_app_object.run_server(host='0.0.0.0', port=9999)