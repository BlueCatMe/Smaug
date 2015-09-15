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

@register_action(u'delete', 'Show details of an item.')
class Delete(ActionBase):
	def update_argparser(self, parser, argv):
		parser.add_argument(u'--by-id', action=u'store_true',
				default=False, help=u"Delete target is item ID.")

	def execute(self, options):

		logger.info(u"Processing DELETE")
		logger.debug(options)

		ret = False

		if options.by_id:
			item = self.service.get_raw(options.target)
		else:
			item = self.service.get(options.target)

		if item != None:
			logger.info(u'Delete {0} ({1})'.format(item[u'title'], item[u'id']))
			ret = self.service.delete(item[u'id'])
		else:
			logger.warn(u'Cannot find the item {0}'.format(options.target))

		return ret

	def show(self, results, options):
		if results:
			logger.info(u'Delete item successfully')
		else:
			logger.info(u'Delete item failed');
