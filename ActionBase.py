#!/usr/bin/python
# coding=utf-8

import os
import platform
import glob
import re

from GoogleDriveService import *

ACTION_DIRNAME = u'actions'

_ACTIONS = []

class ActionConfig(object):
	def __init__(self, cls, action, desc):
		self.cls = cls
		self.action = action
		self.desc = desc

def register_action(action, desc):
	def wrapper(cls):
		if cls in [a.cls for a in _ACTIONS]:
			raise Exception(cls + " is already registered!")
		_ACTIONS.append(ActionConfig(cls, action, desc))
		return cls
	return wrapper

def get_actions():
	action_dir = os.path.join(os.path.dirname(__file__), ACTION_DIRNAME)
	for f in glob.glob(os.path.join(action_dir, u'*.py')):
		modname_ext = os.path.basename(f)
		if modname_ext == u"__init__.py":
			continue
		modname = ACTION_DIRNAME + u"." + os.path.splitext(modname_ext)[0]
		# if the module contains a class (or classes) that are
		# decorated with `register_parser' then the following import
		# will have the side-effect of adding that class (encapsulated
		# in a ParserConfig object) to the _parsers list. Note that
		# this import is effectively a noop if the module has already
		# been imported, so there's no harm in calling get_parsers
		# multiple times.
		__import__(modname)
	return _ACTIONS

def get_action(action):
	for a in _ACTIONS:
		if action == a.action:
			return a
	return None

class ActionBase(object):
	def __init__(self):
		self.data = []
		self.service = None

	def authorize(self, options):
		credentials_storage_path = options.credentials_path
		client_secret_json_path = options.client_secret_json_path

		if not os.path.isfile(client_secret_json_path):
			logger.critical(u"Please prepare %s for Google Drive API usage." % client_secret_json_path)
			return False

		service = GoogleDriveService(client_secret_json_path, credentials_storage_path)
		service.options[u'request_new_credentials'] = options.request_new_credentials
		logger.debug(service.options)

		if service.authorize():
			self.service = service

		return (self.service != None)

	def update_argparser(self, parser):
		pass
	def execute(self, options):
		raise NotImplementedError
	def show(self, results, options):
		pass
