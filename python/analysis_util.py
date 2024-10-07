import yaml
import os
import pandas as pd
import numpy as np


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

def calculate_paired_intra_plate_cv(dict_parameters, pd_df_calibration_concentrations, str_analyte, pd_group):
    if len(pd_group) != 2:
        return np.nan
    str_concentration_column_prefix = dict_parameters["column name prefix for estimated concentrations"]
    estimate_1, estimate_2 = pd_group[f"{str_concentration_column_prefix}{str_analyte}"].values
    mean = (estimate_1 + estimate_2) / 2
    std_dev = np.sqrt((estimate_1 - mean)**2 + (estimate_2 - mean)**2)
    return std_dev / mean

def calculate_paired_intra_plate_rel_abs_diff(dict_parameters, pd_df_calibration_concentrations, str_analyte, pd_group):
    if len(pd_group) != 2:
        return np.nan
    str_concentration_column_prefix = dict_parameters["column name prefix for estimated concentrations"]
    estimate_1, estimate_2 = pd_group[f"{str_concentration_column_prefix}{str_analyte}"].values
    mean = (estimate_1 + estimate_2) / 2
    return np.abs(estimate_1 - estimate_2) / mean

def calculate_max_gradient(dict_parameters, pd_df_calibration_concentrations, str_analyte, pd_group):
    str_gradient_column_prefix = dict_parameters["column name prefix for calibration curve gradient"]
    if len(pd_group) < 2:
        return pd_group[f"{str_gradient_column_prefix}{str_analyte}"].values[0]
    else:
        return np.max(pd_group[f"{str_gradient_column_prefix}{str_analyte}"].values)


def calculate_max_calibration_interval(dict_parameters, pd_df_calibration_concentrations, str_analyte, pd_group):
    list_calibration_intervals = []
    str_concentration_column_prefix = dict_parameters["column name prefix for estimated concentrations"]
    for i in range(len(pd_group)):
        found_group = False
        if (
                pd_group[f"{str_concentration_column_prefix}{str_analyte}"].values[i] <=
                pd_df_calibration_concentrations[f"{str_analyte} Expected"].iloc[0]
        ):
            list_calibration_intervals.append(0)
        else:
            for j in range(len(pd_df_calibration_concentrations) - 1):
                if (
                        (
                                pd_group[f"{str_concentration_column_prefix}{str_analyte}"].values[i] >
                                pd_df_calibration_concentrations[f"{str_analyte} Expected"].iloc[j]
                        ) and
                        (
                                pd_group[f"{str_concentration_column_prefix}{str_analyte}"].values[i] <=
                                pd_df_calibration_concentrations[f"{str_analyte} Expected"].iloc[j + 1]
                        )
                ):
                    list_calibration_intervals.append(j + 1)
                    found_group = True
                    break
            if not found_group:
                list_calibration_intervals.append(len(pd_df_calibration_concentrations))

    return np.max(list_calibration_intervals)


def get_table_of_duplicate_qc_checks(
        dict_parameters,
        pd_df_estimated_concentrations,
        pd_df_calibration_concentrations,
        function_check,
        str_check_name
):
    list_pd_df_estimated_concentrations_checked_one_analyte = []
    for str_analyte in dict_parameters["list of analytes"]:
        pd_df_estimated_concentrations_checked_one_analyte = (
            pd_df_estimated_concentrations
            .groupby(["sample name annotations", "plate number"])
            .apply(
                lambda x: function_check(dict_parameters, pd_df_calibration_concentrations, str_analyte, x),
                include_groups=False
            )
            .reset_index()
        )
        pd_df_estimated_concentrations_checked_one_analyte.columns = ["sample name annotations", "plate number"] + [
            f"{str_check_name} {str_analyte}"]
        # [dict_parameters["column name prefix for calibration curve gradient"] + str_analyte]

        list_pd_df_estimated_concentrations_checked_one_analyte.append(
            pd_df_estimated_concentrations_checked_one_analyte)

    pd_df_estimated_concentrations_checked = list_pd_df_estimated_concentrations_checked_one_analyte[0]
    for pd_df_estimated_concentrations_checked_one_analyte in list_pd_df_estimated_concentrations_checked_one_analyte[
                                                              1:]:
        pd_df_estimated_concentrations_checked = pd.merge(
            pd_df_estimated_concentrations_checked,
            pd_df_estimated_concentrations_checked_one_analyte,
            on=["sample name annotations", "plate number"],
            how="outer"
        )
    return pd_df_estimated_concentrations_checked

def get_table_with_all_duplicate_qc_checks(
        dict_parameters,
        pd_df_estimated_concentrations,
        pd_df_calibration_concentrations
):
    pd_df_CV = get_table_of_duplicate_qc_checks(
        dict_parameters,
        pd_df_estimated_concentrations,
        pd_df_calibration_concentrations,
        calculate_paired_intra_plate_cv,
        "CV"
    )
    pd_df_rel_abs_diff = get_table_of_duplicate_qc_checks(
        dict_parameters,
        pd_df_estimated_concentrations,
        pd_df_calibration_concentrations,
        calculate_paired_intra_plate_rel_abs_diff,
        "rel. abs. diff."
    )
    pd_df_gradients = get_table_of_duplicate_qc_checks(
        dict_parameters,
        pd_df_estimated_concentrations,
        pd_df_calibration_concentrations,
        calculate_max_gradient,
        "max gradient"
    )
    pd_df_calibration_intervals = get_table_of_duplicate_qc_checks(
        dict_parameters,
        pd_df_estimated_concentrations,
        pd_df_calibration_concentrations,
        calculate_max_calibration_interval,
        "max cal interval"
    )
    pd_df_data = pd_df_CV.merge(pd_df_rel_abs_diff, on=["sample name annotations", "plate number"], how="outer")
    pd_df_data = pd_df_data.merge(pd_df_gradients, on=["sample name annotations", "plate number"], how="outer")
    pd_df_data = pd_df_data.merge(pd_df_calibration_intervals, on=["sample name annotations", "plate number"],how="outer")
    return pd_df_data