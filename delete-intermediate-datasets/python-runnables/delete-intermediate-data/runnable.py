import dataiku
import logging
import pandas as pd
import json

from dataiku.runnables import Runnable, ResultTable
from utils import populate_result_table_with_list, append_datasets_to_list

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)

class MyRunnable(Runnable):
    """The base interface for a Python runnable."""

    def __init__(self, project_key, config, plugin_config):
        """
        :param project_key: the project in which the runnable executes
        :param config: the dict of the configuration of the object
        :param plugin_config: contains the plugin settings
        """

        self.project_key = project_key
        self.config = config
        self.plugin_config = plugin_config

    def get_progress_target(self):
        """
        If the runnable will return some progress info, have this function return a tuple of
        (target, unit) where unit is one of: SIZE, FILES, RECORDS, NONE
        """

        return None

    def run(self, progress_callback):

        # Retrieve macro parameters:
        is_dry_run = self.config.get("is_dry_run")
        keep_partitioned = self.config.get("keep_partitioned")
        keep_shared = self.config.get("keep_shared")
        logging.info("DRY RUN is set to {}".format(str(is_dry_run)))
        logging.info("KEEP PARTITIONED is set to {}".format(str(keep_partitioned)))
        logging.info("KEEP SHARED is set to {}".format(str(keep_shared)))

        # Initialize macro result table:
        result_table = ResultTable()
        result_table.add_column("dataset", "Dataset", "STRING")
        result_table.add_column("project_key", "Project Key", "STRING")
        result_table.add_column("type", "Type", "STRING")
        result_table.add_column("action", "Action", "STRING")
        result_table.add_column("action_status", "Action Status", "STRING")
        

        action_status = "Not done (Dry run)" if is_dry_run else "Done"
        
        client = dataiku.api_client()
        #if self.config.get("project_key", None):
            #project = client.get_project(self.config.get("project_key"))
        projects = dataiku.api_client().list_projects()

        all_datasets = []
        all_recipes = []
        project_index = []
        
        # For each project, collect all datasets
        for project in projects:                
            project = dataiku.api_client().get_project(project.get('projectKey'))
            all_datasets.extend( project.list_datasets())
            all_recipes.extend( project.list_recipes() )
        
            for ds in project.list_datasets():
                project_index.append({"name":ds.get("name"),"projectKey":ds.get('projectKey')})
        


        # Build deduplicated lists of input/output datasets:
        input_datasets = []
        output_datasets = []
        for recipe in all_recipes:
            recipe_inputs_dict = recipe["inputs"]
            recipe_outputs_dict = recipe["outputs"]
            # CASE: no input dataset
            if recipe_inputs_dict:
                append_datasets_to_list(recipe_inputs_dict, input_datasets)
            append_datasets_to_list(recipe_outputs_dict, output_datasets)

        # Identify Flow input/outputs:
        flow_inputs = [dataset for dataset in input_datasets if dataset not in output_datasets]
        flow_outputs = [dataset for dataset in output_datasets if dataset not in input_datasets]
        logging.info("Found {} FLOW INPUT datasets: {}".format(str(len(flow_inputs)),
                                                               str(flow_inputs)))
        logging.info("Found {} FLOW OUTPUT datasets: {}".format(str(len(flow_outputs)),
                                                                str(flow_outputs)))
        
        # Identify standalone, intermediate, and partitioned datasets
        standalone_datasets = []
        intermediate_datasets = []
        partitioned_datasets = []

        for dataset in all_datasets:
            if dataset["name"] not in input_datasets + output_datasets:
                standalone_datasets.append(dataset["name"])
            if dataset["name"] not in flow_inputs + flow_outputs + standalone_datasets:
                intermediate_datasets.append(dataset["name"])
            is_partitioned = lambda dataset: len(dataset["partitioning"]["dimensions"]) > 0
            if is_partitioned(dataset):
                partitioned_datasets.append(dataset["name"])

        logging.info("Found {} STANDALONE datasets: {}".format(str(len(standalone_datasets)),
                                                                str(standalone_datasets)))
        logging.info("Found {} INTERMEDIATE datasets: {}".format(str(len(intermediate_datasets)),
                                                                str(intermediate_datasets)))       
        logging.info("Found {} PARTITIONED datasets: {}".format(str(len(partitioned_datasets)),
                                                                str(partitioned_datasets)))

        # Identify shared datasets:
        shared_objects = project.get_settings().settings["exposedObjects"]["objects"]
        shared_datasets = [object["localName"] for object in shared_objects if object["type"]=="DATASET"]
        logging.info("Found {} SHARED datasets: {}".format(str(len(shared_datasets)),
                                                           str(shared_datasets)))


        # Add dataset types to results list
        results = []
        
        datasets = {"STANDALONE":standalone_datasets,
            "INPUT":flow_inputs,
            "OUTPUT":flow_outputs,
            "INTERMEDIATE": intermediate_datasets,
            "SHARED": shared_datasets,
            "PARTITIONED": partitioned_datasets
           }
        df = pd.DataFrame(project_index)
        
        for dataset_type, dataset_type_list in datasets.items():
            for dataset in dataset_type_list:

                dfProjectKey = df[df.name == dataset]["projectKey"]
                
                if len(dfProjectKey) != 1:
                    #logging.info( dfProjectKey )
                    logging.info("Missing dataset {}".format(str( dataset )))
                else:
                    #logging.info(  dfProjectKey.iloc[0] )
                    results.append([dataset, dfProjectKey.iloc[0], dataset_type])
                        
        # Identify which datasets should be kept
        to_keep = standalone_datasets + flow_inputs + flow_outputs
        if keep_partitioned:
            to_keep += partitioned_datasets
        if keep_shared:
            to_keep += shared_datasets
        logging.info("Total of {} datasets to KEEP: {}".format(str(len(to_keep)),
                                                               str(to_keep)))

        # Create df with all results
        results_df = pd.DataFrame(results, columns=["Dataset", "Project Key", "Type"])
        results_grouped = results_df.groupby(["Dataset","Project Key"])['Type'].apply(lambda x: ', '.join(x)).reset_index()
        results_grouped["Action"] = results_grouped["Dataset"].apply(lambda x: "KEEP" if x in to_keep else "CLEAR")
        results_grouped["Status"] = action_status
        #results_df = pd.DataFrame(results, columns=["ProjectKey", "Type"])

        results_grouped = results_grouped.sort_values(by=['Action', 'Type'])


        # Perform cleanup
        to_clear = list(results_grouped["Dataset"][results_grouped['Action']=="CLEAR"])
        logging.info("Total of {} datasets to CLEAR: {}".format(str(len(to_clear)),
                                                               str(to_clear)))

        #print(project.get("test"))
        
        if not is_dry_run:
            for ds in to_clear:
                dfProjectKey = df[df.name == ds]["projectKey"]
                project = client.get_project( dfProjectKey.iloc[0] )
                dataset = project.get_dataset(ds)
                logging.info("Clearing {}...".format(ds))
                dataset.clear()
            logging.info("Clearing {} datasets: done.".format(str(len(to_clear))))

        # Pass results to result table
        for index, row in results_grouped.iterrows():
            result_table.add_record(list(row))
        
        return result_table
