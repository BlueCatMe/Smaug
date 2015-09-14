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

@register_action(u'show', 'Show details of an item.')
class Show(ActionBase):
	def update_argparser(self, parser, argv):
		parser.add_argument(u'--find-path', action=u'store_true',
				default=False, help=u"Find the path of the item.")

	def execute(self, options):

		logger.info(u"Processing SHOW")
		logger.debug(options)

		return self.service.get_raw(options.target)

	def find_path(self, id):
		item = self.service.get_raw(id)
		if item == None:
			return
		if len(item[u'parents']) == 0:
			return

		for p in item[u'parents']:
			self.find_path(p[u'id'])
			sys.stdout.write(u'/{0}'.format(item[u'title']))

	def show(self, results, options):
		pprint.pprint(results)

		if options.find_path:
			print u'Path:'
			for p in results[u'parents']:
				self.find_path(p[u'id'])
				sys.stdout.write(u'/{0}\r\n'.format(results[u'title']))
