# -*- coding: utf-8 -*-
import dataiku
from dataiku import pandasutils as pdu
from dataiku.customrecipe import get_input_names_for_role
from dataiku.customrecipe import get_output_names_for_role
from dataiku.customrecipe import get_recipe_config
import io
import logging
import pandas as pd, numpy as np
from pandas.api.types import is_datetime64_any_dtype as is_datetime
import openpyxl

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='Multi-Sheet Excel Exporter | %(levelname)s - %(message)s')


# Retrieve the list of output folders, should contain unique element
output_folder_id = get_output_names_for_role('folder')
logger.info("Retrieved the following folder ids: {}".format(output_folder_id))
output_folder_name = output_folder_id[0]
logger.info("Received the following output folder name: {}".format(output_folder_name))
output_folder = dataiku.Folder(output_folder_name)


# Retrieve the output folder, should contain unique element
output_folder_id = get_output_names_for_role('folder')
logger.info("Retrieved the following folder ids: {}".format(output_folder_id))
output_folder_name = output_folder_id[0]
logger.info("Received the following output folder name: {}".format(output_folder_name))
output_folder = dataiku.Folder(output_folder_name)

input_config = get_recipe_config()
workbook_name = input_config.get('output_workbook_name', None)
if workbook_name is None:
    logger.warning("Received input received recipe config: {}".format(input_config))
    raise ValueError('Could not read the workbook name.')
    
input_dataset = get_input_names_for_role('input_dataset')[0]

def get_dataset_partitions(dataset_name):
    partitions = dataiku.Dataset(dataset_name).list_partitions(raise_if_empty=True)
    dataset_partitions_df = {}
    for partition in partitions:
        dataset = dataiku.Dataset(dataset_name,ignore_flow = True)  # reinitializing the read partition
        dataset.add_read_partitions(partition)
        dataset_partition_df = dataset.get_dataframe()
        dataset_partitions_df[partition] = dataset_partition_df
    return dataset_partitions_df

dataset_partitions_dict = get_dataset_partitions(input_dataset) 

if 'NP' in dataset_partitions_dict.keys():
    logger.warning("Received input received recipe config: {}".format(input_config))
    raise ValueError('Input dataset must be a partitioned dataset')

# -------------------------------------------------------------------------------- NOTEBOOK-CELL: CODE

def write_to_workbook_bytes(dataset_partitions_dict):
    output = io.BytesIO()
    with pd.ExcelWriter(output) as writer:
        for key in list(dataset_partitions_dict.keys()):
            df = dataset_partitions_dict[key]
            col_list = [column for column in df.columns if is_datetime(df[column])]
            for col in col_list:
                df[col] = df[col].dt.tz_localize(None)
            df.to_excel(writer,sheet_name = key, index = False)
            writer.save()
    return output 
# -------------------------------------------------------------------------------- NOTEBOOK-CELL: CODE
output_df = write_to_workbook_bytes(dataset_partitions_dict)

with output_folder.get_writer(workbook_name + ".xlsx") as w:
    w.write(output_df.getvalue())

