import os
import pandas as pd

def get_base_base_directory_path(dict_parameters):

    str_base_directory_path = dict_parameters["base directory path"]
    if os.environ.get('ON_DOCKER') == 'True':
        str_base_directory_path = dict_parameters["docker base directory path"]
    return str_base_directory_path

def read_clean_adelaide_randomisation_schedule(dict_parameters):
    pd_df_adelaide_randomisation_schedule = pd.read_csv(
        open(
            os.path.join(
                get_base_base_directory_path(dict_parameters),
                dict_parameters["data directory"],
                dict_parameters["randomisation schedule file name"],
            ),
            "r",
        )
    )

    pd_df_adelaide_randomisation_schedule["Rand Number"] = (
            pd_df_adelaide_randomisation_schedule["Rand Number"].str.lstrip('R').str.zfill(4) + 'A'
    )
    pd_df_adelaide_randomisation_schedule.rename(columns={"Rand Number": "patient number"}, inplace=True)

    pd_df_melted_randomisation = pd_df_adelaide_randomisation_schedule.melt(
        id_vars=["patient number"],
        value_vars=["Study Day 1", "Study Day 2"],
        var_name="day",
        value_name="treatment"
    )
    pd_df_melted_randomisation["patient number"] = pd_df_melted_randomisation.apply(
        lambda row: f"{row['patient number']}-D2" if row["day"] == "Study Day 2" else row["patient number"],
        axis=1
    )
    pd_df_melted_randomisation["treatment"] = pd_df_melted_randomisation["treatment"].map(
        {
            "Placebo": 0,
            "Active": 1,
        }
    ).astype(int)
    pd_df_melted_randomisation = pd_df_melted_randomisation.drop(columns=["day"])

    return pd_df_melted_randomisation


#TODO: remove the rbs
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

def read_estimated_concentrations(dict_parameters):

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

def read_plate_data_with_locations(dict_parameters):

    pd_df_estimated_concentrations = pd.read_csv(
        open(
            os.path.join(
                get_base_base_directory_path(dict_parameters),
                dict_parameters["output directory"],
                dict_parameters["plate data with locations file name"]
            ),
            "rb"
        )
    )

    return pd_df_estimated_concentrations

def read_plate_data_with_calibration_concentrations(dict_parameters):

    pd_df_estimated_concentrations = pd.read_csv(
        open(
            os.path.join(
                get_base_base_directory_path(dict_parameters),
                dict_parameters["output directory"],
                dict_parameters["plate data with locations and calibration concentrations file name"],
            ),
            "r"
        )
    )

    return pd_df_estimated_concentrations

def read_quality_control_concentrations(dict_parameters):

    pd_df_quality_control_concentrations = pd.read_csv(
        open(
            os.path.join(
                get_base_base_directory_path(dict_parameters),
                dict_parameters["data directory"],
                dict_parameters["quality control concentrations file name"]
            ),
            "r"
        )
    )

    return pd_df_quality_control_concentrations