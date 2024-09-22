import dash
import dash_auth
from dash import Dash, html, dcc
import yaml

from dashboard_util import read_credentials

dict_parameters = yaml.safe_load(open("../parameters/july_2024_data_parameters.yaml", "r"))
dict_credentials = read_credentials(dict_parameters)

dash_app_object = Dash(
    __name__,
    url_base_pathname = dict_parameters["dashboard url base"],
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
    dash_app_object.run_server(host='0.0.0.0', port=9999, debug=True)