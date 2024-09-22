import os
import pandas as pd

def get_base_base_directory_path(dict_parameters):

    str_base_directory_path = dict_parameters["base directory path"]
    if os.environ.get('ON_DOCKER') == 'True':
        str_base_directory_path = dict_parameters["docker base directory path"]
    return str_base_directory_path
def read_credentials(dict_parameters):

    pd_df_credentials = pd.read_csv(
        open(
            os.path.join(
                get_base_base_directory_path(dict_parameters),
                dict_parameters["dashboard credentials file path"]
            ),
            "rb"
        )
    )
    dict_credentials = dict(zip(pd_df_credentials['username'], pd_df_credentials['password']))

    return dict_credentials

def read_data(dict_parameters):

    pd_df_estimated_concentrations = pd.read_csv(
        open(
            os.path.join(
                get_base_base_directory_path(dict_parameters),
                dict_parameters["output directory"],
                dict_parameters["estimated concentrations file name"]
            ),
            "rb"
        )
    )

    return pd_df_estimated_concentrations