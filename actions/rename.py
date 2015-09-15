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

@register_action(u'rename', 'Rename an item.')
class Rename(ActionBase):
	def update_argparser(self, parser, argv):
		parser.add_argument(u'--by-id', action=u'store_true',
				default=False, help=u"Delete target is item ID.")
		parser.add_argument(u'new_title',
				help=u"new title for this item.")

	def execute(self, options):

		logger.info(u"Processing RENAME")
		logger.debug(options)

		new_item = None

		if options.by_id:
			item = self.service.get_raw(options.target)
		else:
			item = self.service.get(options.target)

		if item != None:
			logger.info(u'Rename {0} ({1}) to {2}'.format(item[u'title'], item[u'id'], options.new_title))
			new_item = self.service.rename(item[u'id'], options.new_title)
		else:
			logger.warn(u'Cannot find the item {0}'.format(options.target))

		return new_item

	def show(self, results, options):
		if results:
			logger.info(u'Rename item to {0} successfully'.format(results[u'title']))
		else:
			logger.info(u'Rename item failed');
