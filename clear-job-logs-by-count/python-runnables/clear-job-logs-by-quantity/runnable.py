from dataiku.runnables import Runnable
import os, shutil
import datetime, time
from cleaning import delete_and_report
from pathlib import Path

class MyRunnable(Runnable):
    def __init__(self, project_key, config, plugin_config):
        self.project_key = project_key
        self.config = config

    def get_progress_target(self):
        return (100, 'NONE')

    def run(self, progress_callback):
        self.dip_home = os.environ['DIP_HOME']
        self.perform_deletion = self.config.get("performDeletion", False)
        self.count = int(self.config.get("count", 0))
        
        if self.config.get('allProjects', False):
            self.project_keys = [project_key for project_key in os.listdir(os.path.join(self.dip_home, 'jobs'))]
        else:
            self.project_keys = [self.project_key]

        self.to_delete = []
        for project_key in self.project_keys:
            project_jobs_folder = os.path.join(self.dip_home, 'jobs', project_key)
            # sort job_name by modified time in ascending order
            sorted_job_names = sorted(Path(project_jobs_folder).iterdir(), key=os.path.getmtime, reverse=True)
            # pick first 'count' to be marked for deletion
            for sorted_job_name in sorted_job_names[self.count:]:
                self.to_delete.append([project_key, sorted_job_name])
            
        html = delete_and_report(self.to_delete, os.path.join(self.dip_home, 'jobs'), progress_callback, self.perform_deletion, 'jobs', ['Project', 'Job'])
        return html

        