#!/usr/bin/python
# coding=utf-8

import os
import sys
import logging

import ActionBase
from ActionBase import get_actions, get_action

from GoogleDriveService import *

from utils import getfilesystemencoding

CLIENT_SECRET_JSON_FILENAME = u'client_secret.json'
CREDENTIALS_STORAGE_FILENAME = u'default.cred'

ACTIONS = [a.action for a in get_actions()]

class StreamHandlerFilter(object):
	def filter(self, record):
		return not record.name.startswith(u'googleapiclient')

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_formatter = logging.Formatter(u'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(stream_formatter)
stream_handler.addFilter(StreamHandlerFilter())
logger.addHandler(stream_handler)

def prepare_argparse_common(parser, argv):
	parser.add_argument(u'action', nargs=1, choices=ACTIONS,
			help=u"what action to do: {0}".format(u','.join(ACTIONS)))
	parser.add_argument(u'--request-new-credentials', action='store_true',
			default=False, help=u"Request new credentials to change account.")
	parser.add_argument(u'--credentials-path', default=os.path.join(os.path.dirname(argv[0]), CREDENTIALS_STORAGE_FILENAME),
			help=u"assign credentials file path.")
	parser.add_argument(u'--client-secret-json-path', default=os.path.join(os.path.dirname(argv[0]), CLIENT_SECRET_JSON_FILENAME),
			help=u"assign client secret json file path.")
	parser.add_argument(u'--log-file', default=None,
			help=u"The remote folder path to upload the documents separated by '/'.")

	parser.add_argument(u'target',
			help=u"target path, can be files or folders")


def handle_options_common(options):
	if options.log_file != None:
		file_handler = logging.FileHandler(options.log_file, mode = u'w', encoding = u'utf-8')
		file_handler.setLevel(logging.DEBUG)
		file_formatter = logging.Formatter(u'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		file_handler.setFormatter(file_formatter)
		logger.addHandler(file_handler)

def main(argv):

	# translate encoding from file system to unicode.
	# pyinstaller will cause os.getfilesystemencoding() return None.
	# wrapper it into a function to return 'UTF-8' by default.
	argv = [a.decode(getfilesystemencoding()) for a in argv]

	# prepare common argument parser and help printer
	parser = argparse.ArgumentParser(description=u'GoogleDrive CLI "Smaug"')
	prepare_argparse_common(parser, argv)

	if len(argv) < 2:
		logger.error("At least two arguments.")
		parser.print_help()
		return -1

	action_name = argv[1]
	logger.info(u"Action: {0}".format(action_name))

	action = get_action(action_name)
	if action == None:
		logger.error(u"Unknown action `{0}'".format(action_name))
		parser.print_help()
		return -1

	# prepare stuff for the action
	action_exec = action.cls()
	action_exec.update_argparser(parser, argv)
	options = parser.parse_args(argv[1:])
	handle_options_common(options)

	if not action_exec.authorize(options):
		logger.error(u"Authorization failed.");
		return -2

	# Rock and Roll!
	results = action_exec.execute(options)

	# show the results
	action_exec.show(results, options)

	return 0

if __name__ == u"__main__":
	main(sys.argv)

