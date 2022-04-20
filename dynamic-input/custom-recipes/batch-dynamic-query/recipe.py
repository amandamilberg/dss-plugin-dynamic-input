# Code for custom code recipe batch-dynamic-query (imported from a Python recipe)

# To finish creating your custom recipe from your original PySpark recipe, you need to:
#  - Declare the input and output roles in recipe.json
#  - Replace the dataset names by roles access in your code
#  - Declare, if any, the params of your custom recipe in recipe.json
#  - Replace the hardcoded params values by acccess to the configuration map

# See sample code below for how to do that.
# The code of your original recipe is included afterwards for convenience.
# Please also see the "recipe.json" file for more information.



# Inputs and outputs are defined by roles. In the recipe's I/O tab, the user can associate one
# or more dataset to each input and output role.
# Roles need to be defined in recipe.json, in the inputRoles and outputRoles fields.

# To  retrieve the datasets of an input role named 'input_A' as an array of dataset names:
# input_A_names = get_input_names_for_role('input_A_role')
# The dataset objects themselves can then be created like this:
# input_A_datasets = [dataiku.Dataset(name) for name in input_A_names]



# For outputs, the process is the same:
# output_A_names = get_output_names_for_role('main_output')
# output_A_datasets = [dataiku.Dataset(name) for name in output_A_names]

# The configuration consists of the parameters set up by the user in the recipe Settings tab.

# Parameters must be added to the recipe.json file so that DSS can prompt the user for values in
# the Settings tab of the recipe. The field "params" holds a list of all the params for wich the
# user will be prompted for values.

# The configuration is simply a map of parameters, and retrieving the value of one of them is simply:

# For optional parameters, you should provide a default value in case the parameter is not present:
# my_variable = get_recipe_config().get('parameter_name', None)

# Note about typing:
# The configuration of the recipe is passed through a JSON object
# As such, INT parameters of the recipe are received in the get_recipe_config() dict as a Python float.
# If you absolutely require a Python int, use int(get_recipe_config()["my_int_param"])

###START HERE
# import the classes/helpers for the plugin
import dataiku
from dataiku.customrecipe import *
import pandas as pd, numpy as np
from dataiku import pandasutils as pdu
from dataiku.sql import SelectQuery, Column, JoinTypes, toSQL
from dataiku.core.sql import SQLExecutor2

### DECLARE AND CREATE DATASET
dynamic_input_table_name = get_input_names_for_role('input_A_role')[0]
output_dataset_name = get_output_names_for_role('output')[0]

dynamic_input_table = dataiku.Dataset(dynamic_input_table_name)
df = dynamic_input_table.get_dataframe()

### GET VARIABLES
# MANDATORY
query_starter = get_recipe_config()['query_starter']
sqlconn = get_recipe_config()['sqlconn']
replace_val_1 = get_recipe_config().get('replace_val_1',None)
replace_col_1 = get_recipe_config().get('replace_col_1',None)
replace_val_2 = get_recipe_config().get('replace_val_2',None)
replace_col_2 = get_recipe_config().get('replace_col_2',None)
replace_val_3 = get_recipe_config().get('replace_val_3',None)
replace_col_3 = get_recipe_config().get('replace_col_3',None)

#############################
# Your original recipe
#############################

executor = SQLExecutor2(connection=sqlconn)

# Compute recipe outputs

# Create dictionary for find/replace
replace_list = [[replace_col_1, replace_val_1],[replace_col_2,replace_val_2],[replace_col_3,replace_val_3]]

# Remove list if empty
replace_list = [i for i in replace_list if None not in i]

num_replacements=len(replace_list)

def write_query(query_starter, dummy_val, dynamic_input):
    query_final = query_starter.replace(dummy_val, str(dynamic_input))
    return query_final

query_in = query_starter
df_output = pd.DataFrame()
flag = 0
for index, row in df.iterrows():
    x = 0
    for input in replace_list:
        col = input[0]
        dummy_val = input[1]
        dynamic_val = row[col]
        query_in = write_query(query_in, dummy_val, dynamic_val)
        if x == num_replacements-1:
            print("EXECUTING QUERY: " + query_in)
            df_out = executor.query_to_df(query_in)
            if flag==0:
                df_output=df_out.copy(deep=True)
                flag = 1
            df_output = df_output.append(df_out, ignore_index = True)
            query_in = query_starter
        x=x+1

# Write recipe outputs
output_dataset = dataiku.Dataset(output_dataset_name)
output_dataset.write_with_schema(df_output)




