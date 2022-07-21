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
group_replacement_value = get_recipe_config()['group_replacement_value']
char_limit = get_recipe_config()['character_limit']
replace_val_1 = get_recipe_config().get('replace_val_1',None)
replace_col_1 = get_recipe_config().get('replace_col_1',None)
replace_val_2 = get_recipe_config().get('replace_val_2',None)
replace_col_2 = get_recipe_config().get('replace_col_2',None)
replace_val_3 = get_recipe_config().get('replace_val_3',None)
replace_col_3 = get_recipe_config().get('replace_col_3',None)
replace_val_4 = get_recipe_config().get('replace_val_4',None)
replace_col_4 = get_recipe_config().get('replace_col_4',None)
replace_val_5 = get_recipe_config().get('replace_val_5',None)
replace_col_5 = get_recipe_config().get('replace_col_5',None)
replace_val_6 = get_recipe_config().get('replace_val_6',None)
replace_col_6 = get_recipe_config().get('replace_col_6',None)
replace_val_7 = get_recipe_config().get('replace_val_7',None)
replace_col_7 = get_recipe_config().get('replace_col_7',None)
replace_val_8 = get_recipe_config().get('replace_val_8',None)
replace_col_8 = get_recipe_config().get('replace_col_8',None)
replace_val_9 = get_recipe_config().get('replace_val_9',None)
replace_col_9 = get_recipe_config().get('replace_col_9',None)
replace_val_10 = get_recipe_config().get('replace_val_10',None)
replace_col_10 = get_recipe_config().get('replace_col_10',None)


#############################
# Your original recipe
#############################

executor = SQLExecutor2(connection=sqlconn)

# Compute recipe outputs

# Create dictionary for find/replace
replace_list = [[replace_col_1, replace_val_1],[replace_col_2,replace_val_2],[replace_col_3,replace_val_3],[replace_col_4, replace_val_4],[replace_col_5,replace_val_5],[replace_col_6,replace_val_6],[replace_col_7, replace_val_7],[replace_col_8,replace_val_8],[replace_col_9,replace_val_9],[replace_col_10, replace_val_10]]

# Remove list if empty
replace_list = [i for i in replace_list if '' not in i and None not in i]
print(replace_list)

num_replacements=len(replace_list)
if num_replacements == 0:
    raise Exception("The number of join keys must be the same for the first and the second datasets")
    
## helper functions to group by IN clause 
def find_query_dict(char_limit, dynamic_input):
    start_idx = 0
    query_dict = {}
    i = 0
    looping = True
    char_limit_num = char_limit
    idx_list = ([pos for pos, char in enumerate(dynamic_input) if char == "," and pos > 950])
    while looping:
        end_idx = min(idx_list, key=lambda x:abs(x-char_limit))
        query = dynamic_input[start_idx:end_idx]
        if query != "":
            if query[0] == ",":
                query = query[1:]
            query_dict[i] = query
            start_idx = end_idx
            char_limit = char_limit + char_limit_num
            i = i + 1
        else:
            looping = False
    return query_dict

def group_for_inclause(df, col, query_starter, char_limit):
    di_list = list(df[col].unique())
    dynamic_input = ",".join(str(d) for d in di_list)
    if len(dynamic_input) <= char_limit:
        return dynamic_input, True
    else:
        dynamic_input_dict = find_query_dict(char_limit, dynamic_input)
        return dynamic_input_dict, False    
    

def write_query(query_starter, dummy_val, dynamic_input):
    query_final = query_starter.replace(dummy_val, str(dynamic_input))
    return query_final


def dynamic_input(df,query_starter,replace_list):
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
    return df_output


def run_plugin(df, replace_list, query_starter, char_limit):
    flag = 0
    if group_replacement_value:
        for input in replace_list:
            col = input[0]
            dummy_val = input[1]
            dynamic_val, single_query = group_for_inclause(df, col, query_starter, char_limit)
            if single_query:
                query_in = write_query(query_starter, dummy_val, dynamic_val)
                print("EXECUTING QUERY: " + query_in)
                df_out = executor.query_to_df(query_in)
                return df_out
            else:
                for key,value in dynamic_val.items():
                    query_in = write_query(query_starter, dummy_val, value)
                    print("EXECUTING QUERY: " + query_in)
                    df_out = executor.query_to_df(query_in)
                    if flag == 0:
                        df_output=df_out.copy(deep=True)
                        flag = 1
                    df_output = df_output.append(df_out, ignore_index = True)
                return df_output
    else:
        return dynamic_input(df, query_starter, replace_list)
    
df_output = run_plugin(df, replace_list, query_starter, char_limit)  
result_df = df_output.drop_duplicates()
    
# Write recipe outputs
output_dataset = dataiku.Dataset(output_dataset_name)
output_dataset.write_with_schema(result_df)




