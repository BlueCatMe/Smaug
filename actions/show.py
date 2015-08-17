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
class List(ActionBase):
	def update_argparser(self, parser, argv):
		pass

	def execute(self, options):

		logger.info(u"Processing SHOW")
		logger.debug(options)

		return self.service.get(options.target)

	def show(self, results, options):
		pprint.pprint(results)
