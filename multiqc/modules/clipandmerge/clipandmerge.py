#!/usr/bin/env python

""" MultiQC module to parse output from ClipAndMerge """

from __future__ import print_function
from collections import OrderedDict
import logging
import os
import re

from multiqc import config
from multiqc.plots import bargraph
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger
log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):
    """ ClipAndMerge module """

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='ClipAndMerge', anchor='clipandmerge',
        href="http://www.github.com/apeltzer/ClipAndMerge",
        info="is a tool for adapter clipping and read merging for ancient DNA data.")

        # Find and load any ClipAndMerge reports
        self.clipandmerge_data = dict()
        for f in self.find_log_files('clipandmerge'):
            self.parse_clipandmerge_log(f)

        # Filter to strip out ignored sample names
        self.clipandmerge_data = self.ignore_samples(self.clipandmerge_data)

        if len(self.clipandmerge_data) == 0:
            raise UserWarning

        log.info("Found {} reports".format(len(self.clipandmerge_data)))

        # Write parsed report data to a file
        self.write_data_file(self.clipandmerge_data, 'multiqc_clipandmerge')

        # Basic Stats Table
        self.clipandmerge_general_stats_table()

        # Alignment Rate Plot
        self.add_section( plot = self.clipandmerge_alignment_plot() )


    def parse_clipandmerge_log(self, f):
        regexes = {
            'total_reads': r"Total reads:\s+(\d+)",
            'reverse_removed': r"Reverse removed:\s+(\d+)",
            'forward_removed': r"Forward removed:\s+(\d+)",
            'merged_removed': r"Merged removed:\s+(\d+)",
            'total_removed': r"Total removed:\s+(\d+)",
            'duplication_rate': r"Duplication Rate:\s+([\d\.]+)",
        }
        parsed_data = dict()
        for k, r in regexes.items():
            r_search = re.search(r, f['f'], re.MULTILINE)
            if r_search:
                parsed_data[k] = float(r_search.group(1))

        try:
            parsed_data['not_removed'] = parsed_data['total_reads'] - parsed_data['reverse_removed'] - parsed_data['forward_removed'] - parsed_data['merged_removed']
        except KeyError:
            log.debug('Could not calculate "not_removed"')

        if len(parsed_data) > 0:
            # TODO: When tool prints input BAM filename, use that instead
            s_name = self.clean_s_name(os.path.basename(f['root']), f['root'])
            self.clipandmerge_data[s_name] = parsed_data

    def clipandmerge_general_stats_table(self):
        """ Take the parsed stats from the ClipAndMerge report and add it to the
        basic stats table at the top of the report """

        headers = OrderedDict()
        headers['duplication_rate'] = {
            'title': 'Duplication Rate',
            'description': 'Percentage of reads categorised as a technical duplicate',
            'min': 0,
            'max': 100,
            'suffix': '%',
            'scale': 'OrRd',
            'format': '{:,.0f}',
            'modify': lambda x: x * 100.0
        }
        self.general_stats_addcols(self.clipandmerge_data, headers)

    def clipandmerge_alignment_plot (self):
        """ Make the HighCharts HTML to plot the duplication rates """

        # Specify the order of the different possible categories
        keys = OrderedDict()
        keys['not_removed'] = { 'name': 'Not Removed' }
        keys['reverse_removed'] = { 'name': 'Reverse Removed' }
        keys['forward_removed'] =   { 'name': 'Forward Removed' }
        keys['merged_removed'] =   { 'name': 'Merged Removed' }

        # Config for the plot
        config = {
            'id': 'clipandmerge_rates',
            'title': 'ClipAndMerge: Deduplicated Reads',
            'ylab': '# Reads',
            'cpswitch_counts_label': 'Number of Reads',
            'hide_zero_cats': False
        }

        return bargraph.plot(self.clipandmerge_data, keys, config)
