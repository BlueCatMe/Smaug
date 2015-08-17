#!/usr/bin/python
# coding=utf-8

import os
import sys
import logging

import datetime
import dateutil.parser
import dateutil.tz

from ActionBase import register_action, ActionBase
from GoogleDriveService import *

from utils import sizeof_fmt

logger = logging.getLogger(__name__)

@register_action(u'list', 'List items in Google Drive')
class List(ActionBase):
	def update_argparser(self, parser, argv):

		parser.add_argument(u'--long', action='store_true',
				default=False, help=u"Use a long listing format.")

	def print_list_item(self, item, options, is_folder = False):
		if is_folder:
			prefix = u'd'
		else:
			prefix = u'f'

		if (options.long):
			if is_folder:
				size_str = u'-'
			else:
				size_str = sizeof_fmt(long(item[u'fileSize']))
			local_dt = dateutil.parser.parse(item[u'modifiedDate']).astimezone(dateutil.tz.tzlocal())

			print u"{0}\t{1:<72}\t{3}\t{4}\t{2}".format(
					prefix,
					item[u'id'],
					item[u'title'],
					datetime.datetime.strftime(local_dt, u'%Y-%m-%d %H:%M:%S %Z'),
					size_str
					).encode('utf-8')
		else:
			print u"{0}\t{1}".format(prefix, item[u'title']).encode('utf-8')

	def execute(self, options):

		logger.info(u"Processing LIST")
		logger.debug(options)

		(dirs, files) = self.service.list(options.target)
		return (dirs, files)


	def show(self, results, options):
		dirs = results[0]
		files = results[1]
		if (options.long):
			print u"{0} dir(s), {1} file(s), Total {2} item(s)".format(len(dirs), len(files), len(dirs) + len(files)).encode('utf-8')
		for f in dirs:
			self.print_list_item(f, options, True)
		for f in files:
			self.print_list_item(f, options, False)
