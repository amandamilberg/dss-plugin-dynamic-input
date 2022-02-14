import logging
import dataiku
from dataiku.customrecipe import *
import pandas as pd, numpy as np
from dataiku import pandasutils as pdu

logger = logging.getLogger(__name__)

# Input datasets
first_dataset = [dataiku.Dataset(name) for name in get_input_names_for_role('left_dataset')][0]
second_dataset = [dataiku.Dataset(name) for name in get_input_names_for_role('right_dataset')][0]
left = first_dataset.get_dataframe()
right = second_dataset.get_dataframe()

# Recipe params
keys_left = get_recipe_config().get('join_keys_1', [])
keys_right = get_recipe_config().get('join_keys_2', [])

output_cols_1 = get_recipe_config().get('output_cols_1', [])
output_cols_2 = get_recipe_config().get('output_cols_2', [])

def get_output_dataset(role):
    names = get_output_names_for_role(role)
    return dataiku.Dataset(names[0]) if len(names) > 0 else None

inner_dataset = get_output_dataset('inner')
left_unmatched_dataset = get_output_dataset('left_unmatched')
right_unmatched_dataset = get_output_dataset('right_unmatched')

# To be used by several functions
dummy_names = ['join_' + str(i) for i in range(len(keys_left))]

#############################
# Your original recipe
#############################

def check_inputs():
    if len(keys_left) != len(keys_right):
        raise Exception("The number of join keys must be the same for the first and the second datasets")
    if len(keys_left) == 0:
        raise Exception("You must select a join key")
    if output_cols_1 != [] and any([k not in output_cols_1 for k in keys_left]):
        raise Exception("You must include the join key in the output column selection for dataset #1")
    if output_cols_2 != [] and any([k not in output_cols_2 for k in keys_right]):
        raise Exception("You must include the join key in the output column selection for dataset #2")
    return None

def drop_na(left, right, keys_left, keys_right):
    """
    Drop the null values in the join columns. 
    
    Note that pandas (unlike postgres) DOES join on nulls, which is why they are removed.
    Also, np.nan == np.nan will result in False, so idk why it joins on nulls. :exploding head:
    These null records will be reinserted in the unmatched datasets.
    
    params
    --------
    left, right : pd.DataFrame
    keys_left, keys_right : pd.DataFrame
    
    returns
    --------
    na_l, na_r : pd.DataFrame of rows with nulls in join key column
    left, right : pd.DataFrame with null rows removed
    """
    join_left_df = left[keys_left]
    join_right_df = right[keys_right]
    
    na_l = left[join_left_df.isna().any(axis=1)]
    na_r = right[join_right_df.isna().any(axis=1)]
    # TODO check whether inplace modifies global scope
    left.drop(index=na_l.index, inplace=True)
    right.drop(index=na_r.index, inplace=True)

    return na_l, na_r, left, right

def set_multiindex(left, right, keys_left, keys_right):
    """
    Sets multi-index from the join keys set by user.
    
    params
    --------
    left, right : pd.DataFrame
    keys_left, keys_right : list of strings
    
    returns
    --------
    left, right : pd.DataFrame with multi-index
    
    """
    # Set multi-index with dummy names
    index_l = pd.MultiIndex.from_frame(left[keys_left], names=dummy_names)
    left = left.set_index(index_l)

    index_r = pd.MultiIndex.from_frame(right[keys_right], names=dummy_names)
    right = right.set_index(index_r)

    return left, right

def inner_join(left, right, keys_left, keys_right):
    """
    Compute inner join between two dataframes.
    
    params
    -------
    left, right : pd.DataFrame with multi-index
    keys_left, keys_right : list of strings
    
    returns
    -------
    merged_df : pd.DataFrame
    
    """
    merged_df = pd.merge(left, right,
                     left_on=dummy_names, right_on=dummy_names,
                     left_index=True, right_index=True,
                     how='inner', suffixes=('_left', '_right'))

    return merged_df

def unjoined(left, right, na_l, na_r, index):
    """
    Compute unjoined datasets and concat with previously dropped null records.
    
    params
    -------
    left, right : pd.DataFrame
    na_l, na_r : pd.DataFrame
    index : pd.Index from inner joined df
    
    returns
    -------
    left_unjoined, right_unjoined: pd.DataFrame
    """

    # Drop the multi-index
    left = left.drop(index=index).reset_index(drop=True)
    right = right.drop(index=index).reset_index(drop=True)

    # Concat the na values
    left_unjoined = pd.concat([left, na_l]).reset_index(drop=True)
    right_unjoined = pd.concat([right, na_r]).reset_index(drop=True)

    return left_unjoined, right_unjoined

def compute_joins(left, right, keys_left, keys_right):
    """
    Computes the inner, left unjoined, and right unjoined datasets.
    
    params
    -------
    left, right : pd.DataFrame
    keys_left, keys_right : list of strings
    
    returns
    -------
    inner : pd.DataFrame
    left_unjoined, right_unjoined : pd.DataFrame
    """
    # Drop na records
    na_l, na_r, left, right = drop_na(left, right, keys_left, keys_right)

    # Set multiindex and compute join
    left, right = set_multiindex(left, right, keys_left, keys_right)
    inner = inner_join(left, right, keys_left, keys_right)

    # Compute unmatched datasets and add back in null records
    left_unjoined, right_unjoined = unjoined(left, right, na_l, na_r, inner.index)

    inner = inner.reset_index(drop=True)

    return inner, left_unjoined, right_unjoined

def keep_output_cols(df, output_cols):
    return df[output_cols]

# Check inputs and run recipe
check_inputs()
logger.info("Done validating inputs")

if output_cols_1 != []:
    logger.info("Removing columns from dataset 1.")
    left = keep_output_cols(left, output_cols_1)
if output_cols_2 != []:
    logger.info("Removing columns from dataset 2.")
    right = keep_output_cols(right, output_cols_2)
    
logger.info("Starting join computation")
inner, left_unjoined, right_unjoined = compute_joins(left, right, keys_left, keys_right)
logger.info("Completed join computation")

# Write recipe outputs
logger.info("Writing datasets")
inner_dataset.write_with_schema(inner)
left_unmatched_dataset.write_with_schema(left_unjoined)
right_unmatched_dataset.write_with_schema(right_unjoined)
