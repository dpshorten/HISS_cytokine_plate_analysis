import argparse
import yaml
import plate_util
import pickle
import os
import calibration_curves

import pandas as pd
pd.options.mode.chained_assignment = None

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--parameters", help="path to the parameters file")
    argparse_namespace = parser.parse_args()

    dict_parameters = yaml.safe_load(open(argparse_namespace.parameters, "r"))

    pd_df_plate_data_with_calibration_concentrations = pd.read_csv(
        open(
            os.path.join(
                dict_parameters["base directory path"],
                dict_parameters["output directory"],
                dict_parameters["plate data with locations and calibration concentrations file name"]
            ),
            "rb"
        ),
        index_col=0
    )

    dict_fitted_calibration_curves = yaml.safe_load(
        open(
            os.path.join(
                dict_parameters["base directory path"],
                dict_parameters["output directory"],
                dict_parameters["fitted calibration curves file name"]
            ),
            "r"
        )
    )

    pd_df_concentrations = calibration_curves.estimate_concentrations(
        dict_parameters,
        pd_df_plate_data_with_calibration_concentrations,
        dict_fitted_calibration_curves
    )

    pd_df_concentrations.to_csv(
        open(
            os.path.join(
                dict_parameters["base directory path"],
                dict_parameters["output directory"],
                dict_parameters["estimated concentrations file name"]
            ),
            "wb"
        ),
        index=False,
    )

if __name__ == "__main__":
    main()