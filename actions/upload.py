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

	def handle_uploaded_file(self, file_path, base = None):
		if base == None:
			base = os.path.dirname(file_path)

		if self.options.move_to_backup_folder != None:
			relative_path = os.path.relpath(file_path, base)
			new_folder_path = os.path.join(self.options.move_to_backup_folder, os.path.dirname(relative_path))

			if not os.path.exists(new_folder_path):
				os.makedirs(new_folder_path)
			try:
				os.rename(file_path, os.path.join(new_folder_path, os.path.basename(file_path)))
				logger.info(u"Move uploaded file {0} to {1}".format(file_path, new_folder_path))
			except WindowsError, err:
				logger.warn(u"Cannot move uploaded file {0} to {1}".format(file_path, new_folder_path))
				logger.warn(exception_format(err))

	def upload_file(self, file_path, base=None, mimetype=None, title=None, parent_id=None):

		if title == None:
			title = os.path.basename(file_path)

		if base == None:
			base = os.path.dirname(file_path)

		files = self.service.query(title = title, parent_id = parent_id, mimeType = GoogleDriveService.MIMETYPE_NON_FOLDER);

		if len(files) > 0:
			logger.info(u"There is {0} file(s) with the same title.".format(len(files)))
			if self.options.conflict_action == u'skip':
				logger.info(u"`{0}' exists, skip it.".format(title))
				if self.options.move_skipped_file:
					self.handle_uploaded_file(file_path, base=base)
				return (files[0], GoogleDriveService.UPLOAD_SKIPPED)
			elif self.options.conflict_action == u'replace':
				logger.info(u"`{0}' exists, replace it.".format(title))
				for file in files:
					logger.info(u"Delete file: {0}".format(file[u'title']))
					self.service.delete(file[u'id'])

		retry_count = GoogleDriveService.DEFAULT_UPLOAD_RETRY_COUNT
		while retry_count > 0:
			(f, r) = self.service.upload_file(file_path, base=base, mimetype=mimetype, title=title, parent_id=parent_id)
			if f != None: # uploaded or skipped
				if (r == GoogleDriveService.UPLOAD_DONE):
					self.handle_uploaded_file(file_path, base=base)
				retry_count = 0
			elif r == GoogleDriveService.UPLOAD_SERVICE_ERROR:
				logger.error("Upload failed due to service error. Try it again..")
				retry_count = retry_count - 1
			else:
				logger.error("Upload failed due to errors cannot be recovered. Give up.")
				retry_count = 0
		return (f, r)

	def upload_folder(self, folder_path, parent_id=None, without_folders = False):

		folder_result = True

		logger.info(u"Uploading folder: {0}".format(folder_path))

		base = os.path.dirname(folder_path)

		# windows returns unicode filename with unicode path.
		for root, dirs, files in os.walk(folder_path):

			relative_path = os.path.relpath(root, base)

			if without_folders:
				parent = make_parent_item(parent_id)
			else:
				parent = self.service.mkdir(relative_path, parent_id)

			for file in files:
				(f, result) = self.upload_file(os.path.join(root, file), base=base, title=file, parent_id=parent[u'id'])
				if f == None:
					folder_result = False

		return folder_result

	def upload(self, path, remote_folder = None, without_folders = False):

		result = False
		parent_id = None

		if remote_folder != None:
			parent = self.service.mkdir(remote_folder.rstrip(u'/'))
			parent_id = parent[u'id']
			# FIXME: should not set service internal member.
			self.service.remote_base = remote_folder

		path = path.rstrip(os.sep)
		logger.info(path)

		if os.path.exists(path):
			if os.path.isdir(path):
				result = self.upload_folder(path, parent_id=parent_id, without_folders=without_folders)
			elif os.path.isfile(path):
				(f, r) = self.upload_file(path, parent_id=parent_id)
				result = (f != None)
			else:
				logger.error(u"Not a file and not a folder!")
		else:
			logger.error(u"{0} does not exist!".format(path))

		return result

	def execute(self, options):

		logger.info(u"Processing UPLOAD")
		logger.debug(options)

		self.options = options

		ret_code = 0
		result = self.upload(options.target,
			remote_folder=options.remote_folder,
			without_folders=options.without_folders)
		if result == True:
			logger.info(u"Uploading `{0}' successed.".format(options.target));
		else:
			logger.warn(u"Uploading `{0}' failed.".format(options.target));
			ret_code = -os.errno.EIO

		return ret_code
