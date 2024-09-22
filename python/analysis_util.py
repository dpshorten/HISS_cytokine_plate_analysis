import yaml
import os
import pandas as pd

def read_parameters_credentials_data(str_parameters_path):
    dict_parameters = yaml.safe_load(open(str_parameters_path, "r"))

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

    pd_df_estimated_concentrations = pd.read_csv(
        open(
            os.path.join(
                dict_parameters["base directory path"],
                dict_parameters["output directory"],
                dict_parameters["estimated concentrations file name"]
            ),
            "rb"
        )
    )

    return dict_parameters, dict_credentials, pd_df_estimated_concentrations

def separate_concentrations_into_cohorts_and_clean(dict_parameters, pd_df_estimated_concentrations):

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

    dict_adelaide_time_string_mapping = {
        'Pre-1hr': '-1hr',
        '15m': '15min',
        '30m': '30min',
        '0.5hr': '30min',
    }
    dict_pd_df_cohort_tables["Adelaide"]["time code"] = (
        dict_pd_df_cohort_tables["Adelaide"]["time code"].map(
            lambda x: x if x not in dict_adelaide_time_string_mapping else dict_adelaide_time_string_mapping[x],
        )
    )

    dict_adelaide_time_code_mapping = {
        '-1hr': 1,
        'Pre-1hr': 1,
        '15min': 2,
        '30min': 3,
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