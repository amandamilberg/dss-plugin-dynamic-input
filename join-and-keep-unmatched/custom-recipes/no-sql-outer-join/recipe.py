import logging
import dataiku
from dataiku.customrecipe import *
import pandas as pd, numpy as np
from dataiku import pandasutils as pdu

logger = logging.getLogger(__name__)

# Input datasets
first_dataset = [dataiku.Dataset(name) for name in get_input_names_for_role('first_dataset')][0]
second_dataset = [dataiku.Dataset(name) for name in get_input_names_for_role('second_dataset')][0]
output_dataset = [dataiku.Dataset(name) for name in get_output_names_for_role('output_dataset')][0]

# Recipe params
first_join_keys = get_recipe_config().get('join_keys_1', [])
second_join_keys = get_recipe_config().get('join_keys_2', [])

output_cols_1 = get_recipe_config().get('output_cols_1', [])
output_cols_2 = get_recipe_config().get('output_cols_2', [])

# Read input datasets
df_left = first_dataset.get_dataframe()
df_right = second_dataset.get_dataframe()

#############################
# Your original recipe
#############################

def check_inputs():
    if len(first_join_keys) != len(second_join_keys):
        raise Exception("The number of join keys must be the same for the first and the second datasets")
    if len(first_join_keys) == 0:
        raise Exception("You must select a join key")
    if output_cols_1 != [] and any([k not in output_cols_1 for k in first_join_keys]):
        raise Exception("You must include the join key in the output column selection for dataset #1")
    if output_cols_2 != [] and any([k not in output_cols_2 for k in second_join_keys]):
        raise Exception("You must include the join key in the output column selection for dataset #2")
    return None

def key_mapping(join_keys, temp_keys):
    return {k:v for k, v in zip(join_keys, temp_keys)}

def join_diff_keys(df_left, df_right):
    # Create temp keys for joining in case there are naming conflicts/redundancies in the datasets
    # Note current implementation fails if non-join col in dataset2 has same name as join key in dataset1
    temp_keys = list(map(lambda x: x + '_temp', first_join_keys))
    inv_map = {k:v for k, v in zip(temp_keys, first_join_keys)}

    df_left.rename(columns=key_mapping(first_join_keys, temp_keys), inplace=True)
    df_right.rename(columns=key_mapping(second_join_keys, temp_keys), inplace=True)
    
    merged_df = (
        pd.merge(
            df_left, 
            df_right, 
            how='outer', 
            on=temp_keys,
            suffixes=('_1','_2')
        )
    .reset_index(drop=True)
    .rename(columns=inv_map)
    )
    return merged_df

def join_diff_keys_alt(df_left, df_right):
    # Outputs two cols for each join key
    merged_df = (
        pd.merge(
            df_left, 
            df_right, 
            how='outer', 
            left_on=first_join_keys,
            right_on=second_join_keys,
            suffixes=('_1','_2')
        )
    .reset_index(drop=True)
    )
    return merged_df
    
def join_same_keys(df_left, df_right):

    merged_df = (
        pd.merge(
            df_left, 
            df_right, 
            how='outer', 
            on=first_join_keys,
            suffixes=('_1','_2')
        )
    .reset_index(drop=True)
    )
    return merged_df

def keep_output_cols(df, output_cols):
    return df[output_cols]

# First, check our inputs
check_inputs()

# Remove cols we don't want to keep
# df_left, df_right = map(keep_output_cols, [df_left, df_right], [output_cols_1, output_cols_2])
if output_cols_1 != []:
    logger.info("Removing columns from dataset 1.")
    df_left = keep_output_cols(df_left, output_cols_1)
if output_cols_2 != []:
    logger.info("Removing columns from dataset 2.")
    df_right = keep_output_cols(df_right, output_cols_2)

# Join datasets
if first_join_keys == second_join_keys:
    logger.info("Execute join with identical keys.")
    merged_df = join_same_keys(df_left, df_right)   
else:
    logger.info("Execute join with different keys.")
    merged_df = join_diff_keys_alt(df_left, df_right)

# Write recipe outputs
output_dataset.write_with_schema(merged_df)