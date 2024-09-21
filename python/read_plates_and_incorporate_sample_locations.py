import argparse
import yaml
import plate_util
import pickle
import os
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--parameters", help="path to the parameters file")
    argparse_namespace = parser.parse_args()

    dict_parameters = yaml.safe_load(open(argparse_namespace.parameters, "r"))
    dict_parsed_file_for_each_plate = plate_util.get_parsed_file_for_each_plate(dict_parameters)
    dict_extracted_plate_data = plate_util.extract_plate_data_and_locations_from_parsed_files(
        dict_parameters,
        dict_parsed_file_for_each_plate,
    )
    dict_plate_sample_locations = plate_util.read_plate_sample_locations(dict_parameters)
    dict_incorporated_plate_data = plate_util.incorporate_plate_sample_locations(
        dict_extracted_plate_data,
        dict_plate_sample_locations
    )
    pd_df_concatenated_plates = plate_util.concatenate_plates_into_single_dataframe(dict_incorporated_plate_data)

    # noinspection PyTypeChecker
    pd_df_concatenated_plates.to_csv(
        open(
            os.path.join(
                dict_parameters["base directory path"],
                dict_parameters["output directory"],
                dict_parameters["plate data with locations file name"]
            ),
            "wb"
        )
    )

if __name__ == "__main__":
    main()