#!/usr/bin/python
# coding=utf-8

import os
import sys
import logging

from ActionBase import register_action, ActionBase
from GoogleDriveService import *

logger = logging.getLogger(__name__)

@register_action(u'upload', 'Upload local files to Google Drive')
class Upload(ActionBase):
	def update_argparser(self, parser, argv):

		parser.add_argument(u'--without-folders', action='store_true',
				default=False, help=u"Do not recreate folder structure in Google Drive.")
		parser.add_argument(u'--move-to-backup-folder', default=None,
				help=u"Move uploaded file to a backup folder.")
		parser.add_argument(u'--move-skipped-file', action=u'store_true',
				default=False, help=u"Move skipped files to backup folder. This option must work with --move-to-backup-folder")
		parser.add_argument(u'--remote-folder', default=None,
				help=u"The remote folder path to upload the documents separated by '/'.")
		parser.add_argument(u'--conflict-action', default=u'skip', choices=[u'skip', u'replace', u'add'],
				help=u"How to handle existing file with the same title")

	def execute(self, options):

		logger.info(u"Processing UPLOAD")
		logger.debug(options)

		# FIXME: workaround because upload implement is still in GoogleService
		self.service.options[u'conflict_action'] = options.conflict_action
		self.service.options[u'move_to_backup_folder'] = options.move_to_backup_folder
		self.service.options[u'move_skipped_file'] = options.move_skipped_file

		ret_code = 0
		result = self.service.upload(options.target,
			remote_folder=options.remote_folder,
			without_folders=options.without_folders)
		if result == True:
			logger.info(u"Uploading `{0}' successed.".format(options.target));
		else:
			logger.warn(u"Uploading `{0}' failed.".format(options.target));
			ret_code = -os.errno.EIO

		return ret_code
