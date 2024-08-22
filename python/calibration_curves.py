from scipy.optimize import curve_fit
import datetime
import numpy as np
import pandas as pd
import math
import functools

def five_parameter_logistic_function(np_x, a, b, c, d, g):
    return d + ((a - d) / np.power((1.0 + (((np.log(np_x) + 1)/ c) ** b)), g))

def four_parameter_logistic_function(np_x, a, b, c, d):
    return d + ((a - d) / (1.0 + (((np.log(np_x) + 1) / c) ** b)))

def get_calibration_curve_function(dict_parameters):

    if dict_parameters["calibration curve model"] == "five parameter logistic":
        return five_parameter_logistic_function
    elif dict_parameters["calibration curve model"] == "four parameter logistic":
        return four_parameter_logistic_function
    else:
        raise ValueError("Invalid calibration curve model specified")

def merge_calibration_concentrations_with_plate_data(
        pd_df_plate_data,
        pd_df_calibration_concentrations
):

    pd_df_merged_plate_data = pd_df_plate_data.copy()

    pd_df_merged_plate_data["sample name annotations"] = (
        pd_df_merged_plate_data["sample name annotations"]
        .str.replace("Standard 0 (Assay Diluent)", "Std 0")
    )

    pd_df_merged_plate_data = pd_df_merged_plate_data.merge(
        pd_df_calibration_concentrations,
        left_on="sample name annotations",
        right_on="Sample ID",
        how="left"
    )

    return pd_df_merged_plate_data

def fit_calibration_curve(dict_parameters, pd_df_plate_data, str_analyte, plate_number):

    np_calibration_concentrations = pd_df_plate_data[str_analyte + " Expected"].values
    np_measured_fluorescent_intensity = pd_df_plate_data[str_analyte + " Mean"].values
    np_measured_fluorescent_intensity_std_dev = pd_df_plate_data[str_analyte + " Std Dev"].values

    try:
        np_fitted_parameters, np_parameter_covariance = curve_fit(
            get_calibration_curve_function(dict_parameters),
            np_calibration_concentrations,  # x
            np_measured_fluorescent_intensity,  # y
            sigma=np_measured_fluorescent_intensity_std_dev,
            #TDDO: add to parameters file
            maxfev=10000
        )
        #print(np_fitted_parameters)
        dict_results = {
            "model": dict_parameters["calibration curve model"],
            "fitted parameters": np_fitted_parameters.tolist(),
        }

    except RuntimeError as e:
        print(f"model fitting failure. plate: {plate_number}, analyte: {str_analyte}")
        print(e)

        dict_results = {
            "model": dict_parameters["calibration curve model"],
            "fitted parameters": "fitting error",
        }

    return dict_results

def fit_calibration_curves(dict_parameters, pd_df_plate_data_with_calibration_concentrations):

    dict_all_calibration_curves = {}

    for plate_number in dict_parameters["plate number to file associations"].keys():

        dict_calibration_curves_for_this_plate = {}

        pd_df_plate_data = (
            pd_df_plate_data_with_calibration_concentrations[
                pd_df_plate_data_with_calibration_concentrations["plate number"] == plate_number
            ]
        )
        pd_df_plate_data = pd_df_plate_data[pd_df_plate_data["sample name annotations"].str.contains("Std")]
        pd_df_plate_data = pd_df_plate_data[~pd_df_plate_data["sample name annotations"].str.contains("Std 0")]

        for str_analyte in dict_parameters["list of analytes"]:

            dict_calibration_curves_for_this_plate[str_analyte] = fit_calibration_curve(
                dict_parameters,
                pd_df_plate_data,
                str_analyte,
                plate_number
            )

        dict_all_calibration_curves[plate_number] = dict_calibration_curves_for_this_plate

    return {
        "fit datetime" : datetime.datetime.now(),
        "calibration curves by plate" : dict_all_calibration_curves
    }

class ConcentrationEstimator:

    def __init__(
            self,
            dict_parameters,
            pd_df_calibration_concentrations,
            dict_fitted_calibration_curves,
            str_analyte,
    ):
        self.str_analyte = str_analyte
        self.dict_fitted_calibration_curves = dict_fitted_calibration_curves
        self.dict_np_calibration_curve_concentrations = {}
        self.dict_np_calibration_curve_fluorescent_intensities = {}

        for plate_number in dict_parameters["plate number to file associations"].keys():

            dict_fit_results = (
                dict_fitted_calibration_curves["calibration curves by plate"][plate_number][str_analyte]
            )
            self.dict_np_calibration_curve_concentrations[plate_number] = np.logspace(
                np.log(min(pd_df_calibration_concentrations[str_analyte + " Expected"])) / np.log(10),
                np.log(max(pd_df_calibration_concentrations[str_analyte + " Expected"])) / np.log(10),
                dict_parameters["calibration curve num points for inverse estimation"],
                base = 10,
            )

            # if self.dict_fit_results["fitted parameters"] == "fitting error":
            # return
            self.dict_np_calibration_curve_fluorescent_intensities[plate_number] = get_calibration_curve_function(dict_parameters)(
                self.dict_np_calibration_curve_concentrations[plate_number],
                *dict_fit_results["fitted parameters"],
            )

    def estimate_concentration(self, pd_series_row):

        measured_fluorescent_intensity = pd_series_row[self.str_analyte + " Mean"]
        plate_number = pd_series_row["plate number"]

        # TODO: Look into better ways to do this
        estimated_concentration = np.interp(
            measured_fluorescent_intensity,
            self.dict_np_calibration_curve_fluorescent_intensities[plate_number],
            self.dict_np_calibration_curve_concentrations[plate_number]
        )

        return np.around(estimated_concentration, 3)

def estimate_concentrations(
        dict_parameters,
        pd_df_plate_data_with_calibration_concentrations,
        dict_fitted_calibration_curves
):

    pd_df_calibration_concentrations = pd_df_plate_data_with_calibration_concentrations[
        pd_df_plate_data_with_calibration_concentrations["sample name annotations"].str.contains("Std")
    ]
    pd_df_calibration_concentrations = pd_df_calibration_concentrations[
        ~pd_df_calibration_concentrations["sample name annotations"].str.contains("Std 0")
    ]
    pd_df_unknowns = pd_df_plate_data_with_calibration_concentrations[
        ~pd_df_plate_data_with_calibration_concentrations["sample name annotations"].str.contains("Std")
    ]

    for str_analyte in dict_parameters["list of analytes"]:
        concentration_estimator = ConcentrationEstimator(
            dict_parameters,
            pd_df_calibration_concentrations,
            dict_fitted_calibration_curves,
            str_analyte
        )

        pd_df_unknowns[dict_parameters["column name prefix for estimated concentrations"] + str_analyte] = (
            pd_df_unknowns.apply(concentration_estimator.estimate_concentration, axis=1)
        )

    list_columns_to_drop = [column_name for column_name in pd_df_unknowns.columns if 'Expected' in column_name]
    list_columns_to_drop.append("Sample ID")
    pd_df_unknowns = pd_df_unknowns.drop(columns=list_columns_to_drop)

    pd_df_unknowns["sample repeat number"] = (
            pd_df_unknowns.groupby("sample name annotations").cumcount() + 1
    )

    list_first_columns = [
        "sample name annotations",
        "sample name plate",
        "sample repeat number",
        "plate number",
        "plate row",
        "plate column",
    ]
    for str_analyte in dict_parameters["list of analytes"]:
        list_first_columns.append(dict_parameters["column name prefix for estimated concentrations"] + str_analyte)
    pd_df_unknowns = (
        pd_df_unknowns[
            list_first_columns +
            [column_name for column_name in pd_df_unknowns.columns if column_name not in list_first_columns]
        ]
    )
    pd_df_unknowns = pd_df_unknowns.sort_values(by=["sample name annotations", "sample repeat number"])

    return pd_df_unknowns


