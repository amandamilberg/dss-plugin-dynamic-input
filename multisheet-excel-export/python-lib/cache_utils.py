#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os
import pwd
import tempfile

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='Plugin: Tableau Hyper API | %(levelname)s - %(message)s')


class CustomTmpFile(object):

    def __init__(self):
        self.cache_relative_dir = '.cache/dss/plugins/multisheet-excel-export'
        self.tmp_output_dir = '/tmp'

    def get_cache_location_from_user_config(self):
        """
        Get the cache location for temporary files creation, the target cache location will be associated
        with the user id that is launching the export
        :return: absolute location of cache
        """
        home_dir = '/tmp/tmp_data'
        cache_absolute_dir = os.path.join(home_dir, self.cache_relative_dir)
        if not os.path.exists(cache_absolute_dir):
            os.makedirs(cache_absolute_dir)
        return cache_absolute_dir

    def get_temporary_cache_file(self, output_file_name):
        """
        Return the path the temporary file in memory
        :param output_file_name:
        :return:
        """
        logger.info("Call to open method in upload exporter ...")
        cache_absolute_path = self.get_cache_location_from_user_config()
        # Create a random file path for the temporary write
        self.tmp_output_dir = tempfile.TemporaryDirectory(dir=cache_absolute_path)
        output_file = os.path.join(self.tmp_output_dir.name, output_file_name)
        return output_file

    def destroy_cache(self):
        """
        Remove cache
        :return:
        """
        self.tmp_output_dir.cleanup()
