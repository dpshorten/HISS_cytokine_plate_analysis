from scipy.optimize import curve_fit
import datetime
import numpy as np
import pandas as pd
import math
import functools

def five_parameter_logistic_function(np_x, a, b, c, d, g):
    return d + ((a - d) / np.power((1.0 + (((np_x + 1)/ c) ** b)), g))

def four_parameter_logistic_function(np_x, a, b, c, d):
    return d + ((a - d) / (1.0 + ((np_x + 1) / c) ** b))

def get_calibration_curve_concenration_points(dict_parameters, float_max_concentration):
    # return np.logspace(
    #     0,
    #     np.log(float_max_concentration) / np.log(10),
    #     int(dict_parameters["calibration curve num points for inverse estimation"]),
    #     base = 10,
    # )
    return np.linspace(
        0,
        float_max_concentration,
        int(dict_parameters["calibration curve num points for inverse estimation"]),
    )
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

def fit_calibration_curve(
        dict_parameters,
        np_calibration_concentrations,
        np_measured_fluorescent_intensity,
        np_measured_fluorescent_intensity_std_dev,
        plate_number,
        str_analyte
):
    try:
        np_fitted_parameters, np_parameter_covariance = curve_fit(
            get_calibration_curve_function(dict_parameters),
            np_calibration_concentrations,  # x
            np_measured_fluorescent_intensity,  # y
            sigma=np_measured_fluorescent_intensity_std_dev,
            # TDDO: add to parameters file
            maxfev=int(dict_parameters["calibration curve maxfev"])
        )
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

def fit_calibration_curve_with_left_out_points(
        dict_parameters,
        plate_number,
        str_analyte,
        np_calibration_concentrations,
        np_measured_fluorescent_intensity,
        np_measured_fluorescent_intensity_std_dev,
        list_left_out_indices
):
    np_calibration_concentrations_temp = np.delete(np_calibration_concentrations, list_left_out_indices)
    if "calibration concentration modifier" in dict_parameters["plate number to file associations"][plate_number].keys():
        np_calibration_concentrations_temp = (
                np_calibration_concentrations_temp *
                dict_parameters["plate number to file associations"][plate_number]["calibration concentration modifier"]
        )

    np_measured_fluorescent_intensity_temp = np.delete(np_measured_fluorescent_intensity, list_left_out_indices)
    np_measured_fluorescent_intensity_std_dev_temp = np.delete(np_measured_fluorescent_intensity_std_dev, list_left_out_indices)

    dict_fit_results = fit_calibration_curve(
        dict_parameters,
        np_calibration_concentrations_temp,
        np_measured_fluorescent_intensity_temp,
        np_measured_fluorescent_intensity_std_dev_temp,
        plate_number,
        str_analyte
    )

    return dict_fit_results

def one_iteration_of_greedy_LOO(
        dict_parameters,
        plate_number,
        str_analyte,
        np_calibration_concentrations,
        np_measured_fluorescent_intensity,
        np_measured_fluorescent_intensity_std_dev,
        list_calibration_names,
        dict_left_out_indices
):
    index_of_highest_LOO_statistic = -1
    highest_LOO_statistic = 0
    list_left_out_indices = [dict_left_out_indices[key]["left out index"] for key in dict_left_out_indices.keys()]
    for i in range(len(np_calibration_concentrations)):
        if np_calibration_concentrations[i] == 0:
            continue

        dict_fit_results_temp = fit_calibration_curve_with_left_out_points(
            dict_parameters,
            plate_number,
            str_analyte,
            np_calibration_concentrations,
            np_measured_fluorescent_intensity,
            np_measured_fluorescent_intensity_std_dev,
            list_left_out_indices + [i],
        )

        if dict_fit_results_temp["fitted parameters"] == "fitting error":
            return dict_fit_results_temp

        np_fitted_parameters = dict_fit_results_temp["fitted parameters"]
        np_calibration_curve_points = get_calibration_curve_concenration_points(
            dict_parameters,
            max(np_calibration_concentrations)
        )
        np_fitted_fluorescent_intensities = get_calibration_curve_function(dict_parameters)(
            np_calibration_curve_points,
            *np_fitted_parameters
        )
        estimated_LOO_fluorescent_intensity = np.interp(
            np_calibration_concentrations[i],
            np_calibration_curve_points,
            np_fitted_fluorescent_intensities,
        )

        float_LOO_statistic = float(
            np.abs(
                estimated_LOO_fluorescent_intensity - np_measured_fluorescent_intensity[i]
            )
            / np_measured_fluorescent_intensity[i]
        )
        if (
                (float_LOO_statistic > highest_LOO_statistic) and
                (i not in list_left_out_indices) and
                list_calibration_names[i] not in dict_left_out_indices
        ):
            highest_LOO_statistic = float_LOO_statistic
            index_of_highest_LOO_statistic = i

    return highest_LOO_statistic, index_of_highest_LOO_statistic
def fit_calibration_curve_and_perform_LOO(
        dict_parameters,
        pd_df_plate_data,
        str_analyte,
        plate_number
):

    np_calibration_concentrations = pd_df_plate_data[str_analyte + " Expected"].values
    list_calibration_names = pd_df_plate_data["sample name annotations"].values
    list_calibration_rows = pd_df_plate_data["plate row"].values
    list_calibration_columns = pd_df_plate_data["plate column"].values
    np_measured_fluorescent_intensity = (
        pd_df_plate_data[str_analyte + " " + dict_parameters["quantity for estimation"]].values
    )
    np_measured_fluorescent_intensity_std_dev = pd_df_plate_data[str_analyte + " Std Dev"].values

    if dict_parameters["perform LOO check on calibration points"]:
        # Note that the keys of this dictionary are the names of the calibration standards
        # This is because we do not want to leave out a standard twice
        dict_left_out_indices = {}
        # TODO: change this to a greedy approach
        highest_LOO_statistic = dict_parameters["LOO check threshold"] + 1
        while highest_LOO_statistic > dict_parameters["LOO check threshold"]:

            highest_LOO_statistic, index_of_highest_LOO_statistic = one_iteration_of_greedy_LOO(
                dict_parameters,
                plate_number,
                str_analyte,
                np_calibration_concentrations,
                np_measured_fluorescent_intensity,
                np_measured_fluorescent_intensity_std_dev,
                list_calibration_names,
                dict_left_out_indices
            )

            if (highest_LOO_statistic > dict_parameters["LOO check threshold"]):
                if list_calibration_names[index_of_highest_LOO_statistic] in dict_left_out_indices:
                    if (
                            highest_LOO_statistic >
                            dict_left_out_indices[list_calibration_names[index_of_highest_LOO_statistic]]["LOO statistic"]
                    ):
                        dict_left_out_indices[list_calibration_names[index_of_highest_LOO_statistic]] = {
                            "left out index": index_of_highest_LOO_statistic,
                            "LOO statistic": highest_LOO_statistic,
                            "plate row": list_calibration_rows[index_of_highest_LOO_statistic],
                            "plate column": int(list_calibration_columns[index_of_highest_LOO_statistic]),
                        }
                else:
                    dict_left_out_indices[list_calibration_names[index_of_highest_LOO_statistic]] = {
                        "left out index": index_of_highest_LOO_statistic,
                        "LOO statistic": highest_LOO_statistic,
                        "plate row": list_calibration_rows[index_of_highest_LOO_statistic],
                        "plate column": int(list_calibration_columns[index_of_highest_LOO_statistic]),
                    }

        list_left_out_indices = [dict_left_out_indices[key]["left out index"] for key in dict_left_out_indices.keys()]
        dict_fit_results = fit_calibration_curve_with_left_out_points(
            dict_parameters,
            plate_number,
            str_analyte,
            np_calibration_concentrations,
            np_measured_fluorescent_intensity,
            np_measured_fluorescent_intensity_std_dev,
            list_left_out_indices
        )
        dict_fit_results["dict LOO results"] = dict_left_out_indices

    else:
        dict_fit_results = fit_calibration_curve(
            dict_parameters,
            np_calibration_concentrations,
            np_measured_fluorescent_intensity,
            np_measured_fluorescent_intensity_std_dev,
            plate_number,
            str_analyte
        )

    return dict_fit_results

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
        #pd_df_plate_data = pd_df_plate_data[~pd_df_plate_data["sample name annotations"].str.contains("Std 0")]

        for str_analyte in dict_parameters["list of analytes"]:

            dict_calibration_curves_for_this_plate[str_analyte] = fit_calibration_curve_and_perform_LOO(
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
            # self.dict_np_calibration_curve_concentrations[plate_number] = np.logspace(
            # 0,
            #     np.log(max(pd_df_calibration_concentrations[str_analyte + " Expected"])) / np.log(10),
            #     int(dict_parameters["calibration curve num points for inverse estimation"]),
            #     base = 10,
            # )
            self.dict_np_calibration_curve_concentrations[plate_number] = get_calibration_curve_concenration_points(
                dict_parameters,
                max(pd_df_calibration_concentrations[str_analyte + " Expected"])
            )

            # if self.dict_fit_results["fitted parameters"] == "fitting error":
            # return
            self.dict_np_calibration_curve_fluorescent_intensities[plate_number] = get_calibration_curve_function(dict_parameters)(
                self.dict_np_calibration_curve_concentrations[plate_number],
                *dict_fit_results["fitted parameters"],
            )

    def estimate_concentration(self, pd_series_row, dict_parameters):

        measured_fluorescent_intensity = (
            pd_series_row[self.str_analyte + " " + dict_parameters["quantity for estimation"]]
        )
        plate_number = pd_series_row["plate number"]

        # TODO: Look into better ways to do this
        estimated_concentration = np.interp(
            measured_fluorescent_intensity,
            self.dict_np_calibration_curve_fluorescent_intensities[plate_number],
            self.dict_np_calibration_curve_concentrations[plate_number]
        )

        index_of_nearest_fluorescent_intensity = np.searchsorted(
            self.dict_np_calibration_curve_fluorescent_intensities[plate_number],
            measured_fluorescent_intensity,
            side='right'
        )

        index_of_nearest_fluorescent_intensity = min(
            index_of_nearest_fluorescent_intensity,
            len(self.dict_np_calibration_curve_fluorescent_intensities[plate_number]) - 2
        )

        float_gradient = (
            (self.dict_np_calibration_curve_fluorescent_intensities[plate_number][index_of_nearest_fluorescent_intensity + 1] -
            self.dict_np_calibration_curve_fluorescent_intensities[plate_number][index_of_nearest_fluorescent_intensity])/
            (self.dict_np_calibration_curve_concentrations[plate_number][index_of_nearest_fluorescent_intensity + 1] -
             self.dict_np_calibration_curve_concentrations[plate_number][index_of_nearest_fluorescent_intensity])
        )

        # TODO: Maybe do rounding further down the pipeline
        return pd.Series([np.around(estimated_concentration, 3), float_gradient])

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

        pd_df_unknowns[[
            dict_parameters["column name prefix for estimated concentrations"] + str_analyte,
            dict_parameters["column name prefix for calibration curve gradient"] + str_analyte,
        ]] = (
            pd_df_unknowns.apply(
                lambda pd_series_row: concentration_estimator.estimate_concentration(
                    pd_series_row, dict_parameters
                ), axis=1
            )
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


