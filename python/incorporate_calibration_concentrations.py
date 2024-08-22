import argparse
import yaml
import plate_util
import os
import calibration_curves

import pandas as pd
pd.options.mode.chained_assignment = None

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--parameters", help="path to the parameters file")
    argparse_namespace = parser.parse_args()

    dict_parameters = yaml.safe_load(open(argparse_namespace.parameters, "r"))

    pd_df_plate_data = pd.read_csv(
        open(
            os.path.join(
                dict_parameters["output directory path"],
                dict_parameters["plate data with locations file name"]
            ),
            "rb"
        ),
        index_col=0
    )

    pd_df_calibration_concentrations = plate_util.read_and_clean_calibration_concentrations(dict_parameters)

    pd_df_plate_data_with_calibration_concentrations = calibration_curves.merge_calibration_concentrations_with_plate_data(
        pd_df_plate_data,
        pd_df_calibration_concentrations
    )

    pd_df_plate_data_with_calibration_concentrations.to_csv(
        open(
            os.path.join(
                dict_parameters["output directory path"],
                dict_parameters["plate data with locations and calibration concentrations file name"]
            ),
            "wb"
        )
    )

if __name__ == "__main__":
    main()