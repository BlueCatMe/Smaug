#!/usr/bin/python
# coding=utf-8

import os
import sys
import logging

from ActionBase import register_action, ActionBase
from GoogleDriveService import *

logger = logging.getLogger(__name__)

@register_action(u'list', 'List items in Google Drive')
class List(ActionBase):
	def update_argparser(self, parser, argv):

		parser.add_argument(u'target',
				help=u"target path, can be files or folders")

		parser.add_argument(u'--long', action='store_true',
				default=False, help=u"Use a long listing format.")

	def print_list_item(self, item, options, is_folder = False):
		if is_folder:
			prefix = u'd'
		else:
			prefix = u'f'

		if (options.long):
			print u"{0}\t{1}\t{2}".format(prefix, item[u'id'], item[u'title'])
		else:
			print u"{0}\t{1}".format(prefix, item[u'title'])

	def execute(self, options):

		logger.info(u"Processing LIST")
		logger.debug(options)

		(dirs, files) = self.service.list(options.target)
		return (dirs, files)


	def show(self, results, options):
		dirs = results[0]
		files = results[1]
		if (options.long):
			print u"{0} dir(s), {1} file(s), Total {2} item(s)".format(len(dirs), len(files), len(dirs) + len(files))
		for f in dirs:
			self.print_list_item(f, options, True)
		for f in files:
			self.print_list_item(f, options, False)
