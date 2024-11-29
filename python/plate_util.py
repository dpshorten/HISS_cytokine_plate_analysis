import pandas as pd
import io
from functools import reduce
import os

def read_plate_sample_name_corrections(dict_parameters):

        pd_df_sample_name_corrections = pd.read_csv(
            open(
                os.path.join(
                    dict_parameters["base directory path"],
                    dict_parameters["data directory"],
                    dict_parameters["plate sample locations relative path"],
                    dict_parameters["sample name corrections file name"],
                ),
                "r",
            )
        )

        return pd_df_sample_name_corrections

def split_file_lines_into_blocks(file_object):
    """ Split a file into blocks of lines separated by empty lines """

    list_of_blocks = []
    list_of_lines_in_block = []

    for str_line in file_object:
        if str_line.strip("\n ,"):
            list_of_lines_in_block.append(str_line)
        elif list_of_lines_in_block:
            list_of_blocks.append(list_of_lines_in_block)
            list_of_lines_in_block = []

    if list_of_lines_in_block:
        list_of_blocks.append(list_of_lines_in_block)

    return list_of_blocks

def parse_standard_line(str_line):

    list_line_data = str_line.strip("\n ,").split(',')
    
    for i in range(len(list_line_data)):
        list_line_data[i] = list_line_data[i].strip('"')
    
    # Remove empty strings    
    list_line_data = [element for element in list_line_data if element]

    return list_line_data[0], ", ".join(list_line_data[1:],)

def parse_standard_metadata_block(list_of_lines):

    dict_block_data = {}

    for str_line in list_of_lines:
        str_first_element, str_remaining_elements = parse_standard_line(str_line)
        dict_block_data[str_first_element] = str_remaining_elements

    return dict_block_data

def parse_tabular_block(list_of_lines, include_sample_column=True):

    list_of_lines = [line.strip("\n ,") for line in list_of_lines]

    str_data_type_descriptor = list_of_lines[0].split(',')[1].strip('"')

    # Leave out the Avg MFI block as it does not contain locations
    if str_data_type_descriptor == "Avg MFI":
        return None

    pd_df_block_table = pd.read_csv(
        io.StringIO('\n'.join(list_of_lines[1:])),
        quotechar='"',
    )
    pd_df_block_table.columns = [
        pd_df_block_table.columns[i] + " " + str_data_type_descriptor if i > 1 else pd_df_block_table.columns[i]
        for i in range(len(pd_df_block_table.columns))
    ]

    if not include_sample_column:
        pd_df_block_table = pd_df_block_table.drop(columns=["Sample"])

    # Plate 3 had extra rows with empty columns, so we handle that here
    pd_df_block_table = pd_df_block_table.dropna()

    return pd_df_block_table

def parse_intelliflex_file(
        str_file_path,
        include_sample_column=True):
    """
    For the file Plate_03_and_Plate_3_RunResults_Multiplate_2024-04-04_13-35-52_1.csv,
    there is an inconsistency in the pairing of the sample and location columns.
    This is the reason for giving the option to not include the sample column. Eg: For the median, location (1, A2)
    corresponds to sample unknown7, whereas for the mean, location (1, A2) corresponds to sample unknown14.

    The option merge_on_both_sample_and_location is used to merge the tables on both the location and sample columns.
    If it is false, the tables are merged only on the location column.
    """

    dict_all_blocks = {}

    with open(str_file_path, 'r', encoding='utf-8-sig') as file_object:

        list_of_blocks = split_file_lines_into_blocks(file_object)

        dict_all_blocks["header"] = parse_standard_metadata_block(list_of_blocks[0])
        dict_all_blocks["main metadata block"] = parse_standard_metadata_block(list_of_blocks[1])
        dict_all_blocks["calibration results"] = parse_standard_metadata_block(list_of_blocks[2][1:])
        dict_all_blocks["calibration info"] = parse_standard_metadata_block(list_of_blocks[3][1:])

        list_pd_df_block_tables = []
        # Note that we leave out the last 2 blocks and CRC number
        for list_block_lines in list_of_blocks[6:-3]:
            pd_df_block_table = parse_tabular_block(list_block_lines, include_sample_column=include_sample_column)
            if pd_df_block_table is not None:
                list_pd_df_block_tables.append(pd_df_block_table)

        list_merge_columns = ["Location"]
        if include_sample_column:
            list_merge_columns = ["Location", "Sample"]
        dict_all_blocks["merged tables dataframe"] = reduce(
            lambda x, y: pd.merge(x, y, how="left", on=list_merge_columns),
            list_pd_df_block_tables
        )

    return dict_all_blocks

def get_parsed_file_for_each_plate(dict_parameters):

    dict_parsed_file_for_each_plate = {}
    for plate_number in dict_parameters["plate number to file associations"].keys():
        dict_parsed_file_for_each_plate[plate_number] = parse_intelliflex_file(
            os.path.join(
                dict_parameters["base directory path"],
                dict_parameters["data directory"],
                dict_parameters["plate number to file associations"][plate_number]["file name"]
            )
        )

    return dict_parsed_file_for_each_plate

def read_plate_sample_locations(dict_parameters):

    # Use a dict instead of list, so that we can keep the same indexing as the original plate files
    dict_plate_sample_locations = {}
    for i in dict_parameters["plate number to file associations"].keys():
        # noinspection PyTypeChecker
        dict_plate_sample_locations[i] = pd.read_csv(
            os.path.join(
                dict_parameters["base directory path"],
                dict_parameters["data directory"],
                dict_parameters["plate sample locations relative path"],
                "{prefix}{i}.csv".format(prefix=dict_parameters["plate sample locations file name prefix"], i=i),
            ),
            index_col=0
        )

    return dict_plate_sample_locations

def read_and_clean_calibration_concentrations(dict_parameters, str_base_directory_path=None):

    if str_base_directory_path is None:
        str_base_directory_path = dict_parameters["base directory path"]
    pd_df_calibration_concentrations = pd.read_excel(
        os.path.join(
            str_base_directory_path,
            dict_parameters["data directory"],
            dict_parameters["calibration concentrations file name"]
        )
    )

    # Get the format the same as in the sample locations files
    pd_df_calibration_concentrations["Sample ID"] = (
        pd_df_calibration_concentrations["Sample ID"].str.replace("Standard", "Std ")
    )
    pd_df_calibration_concentrations["Sample ID"] = (
        pd_df_calibration_concentrations["Sample ID"].str.replace("Background", "Std ")
    )
    pd_df_calibration_concentrations = pd_df_calibration_concentrations.drop_duplicates()


    pd_df_calibration_concentrations = (
        pd_df_calibration_concentrations.pivot(columns="Analyte", values="Expected", index="Sample ID")
        .reset_index()
    )
    pd_df_calibration_concentrations = pd_df_calibration_concentrations.rename(
        columns={col: col + " Expected" for col in pd_df_calibration_concentrations.columns[1:]}
    )
    pd_df_calibration_concentrations = pd_df_calibration_concentrations.rename(
        columns={"Analyte": "Sample ID"}
    )
    pd_df_calibration_concentrations.index.name = None

    return pd_df_calibration_concentrations

def extract_plate_data_and_locations_from_parsed_files(dict_parameters, dict_parsed_files):

    dict_extracted_plate_data = {}
    for plate_number in dict_parsed_files.keys():
        pd_df_merged_tables = dict_parsed_files[plate_number]["merged tables dataframe"]
        pd_df_merged_tables["Location"] = (
            pd_df_merged_tables["Location"]
            .replace(r'^\d+', '', regex=True) # remove leading number
            .str.strip("()") # remove parentheses
        )

        pd_df_merged_tables[["file plate number", "location code"]] = (
            pd_df_merged_tables["Location"].str.split(",", expand = True)
        )
        pd_df_merged_tables["file plate number"] = pd_df_merged_tables["file plate number"].astype(int)
        pd_df_merged_tables["plate row"] = pd_df_merged_tables["location code"].str[0]
        pd_df_merged_tables["plate column"] = pd_df_merged_tables["location code"].str[1:].astype(int)

        if "file plate number" in dict_parameters["plate number to file associations"][plate_number].keys():
            file_plate_number = dict_parameters["plate number to file associations"][plate_number]["file plate number"]
        else:
            file_plate_number = 1

        pd_df_merged_tables = (
            pd_df_merged_tables[
                pd_df_merged_tables["file plate number"] == file_plate_number
            ]
        )
        pd_df_merged_tables = pd_df_merged_tables.drop(columns=["Location", "location code", "file plate number"])
        pd_df_merged_tables = pd_df_merged_tables.reset_index(drop=True)
        pd_df_merged_tables["plate number"] = plate_number

        # reorder the columns
        pd_df_merged_tables = (
            pd_df_merged_tables[
                ["plate number", "plate row", "plate column"] +
                [col for col in pd_df_merged_tables if col not in ["plate number", "plate row", "plate column"]]
                ]
        )

        dict_extracted_plate_data[plate_number] = pd_df_merged_tables


    return dict_extracted_plate_data

def incorporate_plate_sample_locations(dict_extracted_plate_data, dict_plate_sample_locations):

    dict_incorporated_plate_data = {}
    for plate_number in dict_extracted_plate_data.keys():

        pd_df_melted_sample_locations = (
            dict_plate_sample_locations[plate_number]
            .reset_index()
            .rename(columns={"index": "plate row"})
            .melt(id_vars=["plate row"], value_vars=dict_plate_sample_locations[plate_number].columns)
            .rename(columns={"variable": "plate column", "value": "sample name annotations"})
        )
        pd_df_melted_sample_locations["plate column"] = pd_df_melted_sample_locations["plate column"].astype(int)

        pd_df_merged = pd.merge(
            dict_extracted_plate_data[plate_number],
            pd_df_melted_sample_locations,
            on=["plate row", "plate column"]
        )
        pd_df_merged = pd_df_merged.rename(columns={"Sample": "sample name plate"})
        columns = pd_df_merged.columns.tolist()
        columns = columns[:3] + columns[-1:] + columns[3:-1]
        pd_df_merged = pd_df_merged[columns]

        pd_df_merged = pd_df_merged.dropna(subset=["sample name annotations"])

        dict_incorporated_plate_data[plate_number] = pd_df_merged

    return dict_incorporated_plate_data

def concatenate_plates_into_single_dataframe(dict_incorporated_plate_data):

    pd_df_concatenated = pd.concat(dict_incorporated_plate_data.values(), ignore_index=True)
    return pd_df_concatenated

def apply_sample_name_corrections(dict_parameters, pd_df_concatenated_plates):

    pd_df_sample_name_corrections = read_plate_sample_name_corrections(dict_parameters)

    pd_df_merged = pd_df_concatenated_plates.merge(
        pd_df_sample_name_corrections,
        left_on=["sample name annotations", "plate number", "plate row", "plate column"],
        right_on=["Old ID", "Plate #", "Row", "Column"],
        how="left"
    )

    set_unmerged_ids = set(pd_df_sample_name_corrections['New ID']) - set(pd_df_merged['New ID'])

    if set_unmerged_ids:
        print("The following sample name corrections did not have a match in the plate data:")
        print(set_unmerged_ids)
        raise AssertionError("Some sample name corrections did not match")

    # pd_df_merged[pd_df_merged["New ID"].isna()]["sample name annotations"] = (
    #     pd_df_merged[pd_df_merged["New ID"].isna()]["New ID"]
    # )

    pd_df_merged.loc[~pd_df_merged["New ID"].isna(), "sample name annotations"] = (
        pd_df_merged.loc[~pd_df_merged["New ID"].isna(), "New ID"]
    )

    pd_df_merged = pd_df_merged.drop(columns=["Plate #", "Row", "Column", "New ID"])
    pd_df_merged = pd_df_merged.rename(columns={"Old ID": "old sample name annotations"})

    # reorder the columns
    pd_df_merged = (
        pd_df_merged[
            ["plate number", "plate row", "plate column", "sample name annotations", "old sample name annotations"] +
            [
                col for col in pd_df_merged if col not in
                ["plate number", "plate row", "plate column", "sample name annotations", "old sample name"]
            ]
        ]
    )

    return pd_df_merged