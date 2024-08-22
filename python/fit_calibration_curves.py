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
                dict_parameters["output directory path"],
                dict_parameters["plate data with locations and calibration concentrations file name"]
            ),
            "rb"
        ),
        index_col=0
    )

    dict_calibration_results = calibration_curves.fit_calibration_curves(
        dict_parameters,
        pd_df_plate_data_with_calibration_concentrations
    )

    yaml.dump(
        dict_calibration_results,
        open(
            os.path.join(
                dict_parameters["output directory path"],
                dict_parameters["fitted calibration curves file name"]
            ),
            "w"
        )
    )

if __name__ == "__main__":
    main()