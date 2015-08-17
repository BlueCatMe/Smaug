#!/usr/bin/python
# coding=utf-8

import os
import sys
import logging

from utils import *
from ActionBase import register_action, ActionBase
from GoogleDriveService import *

logger = logging.getLogger(__name__)

@register_action(u'download', 'Download items from Google Drive')
class Download(ActionBase):
	def __init__(self):
		self.data = []
		self.options = None

	def update_argparser(self, parser, argv):

		parser.add_argument(u'--output-folder', default=None,
				help=u"The local folder path to store downloaded files separated by '{0}'.".format(os.sep))

		parser.add_argument(u'--check-md5sum', action=u'store_true',
				default=False, help=u"Check downloaded file md5 sum.")

		parser.add_argument(u'--remove-incorrect-download', action=u'store_true',
				default=False, help=u"Remove incorrect downloaded files.")

		parser.add_argument(u'--conflict-action', default=u'skip', choices=[u'skip', u'add', u'skip_strict'],
				help=u"How to handle existing file with the same title")

		parser.add_argument(u'--try-to-resume', action=u'store_true',
				default=False, help=u"Try to resume interrupted download.")

	def handle_incorrect_downloaded_file(self, tmp_path):
		if not os.path.isfile(tmp_path):
			logger.error(u'{0} does not exist!'.format(tmp_path))
			return True

		ret = False
		try:
			if (self.options.remove_incorrect_download):
				os.unlink(tmp_path)
				logger.info(u'Remove incorrect file {0}'.format(tmp_path));
			ret = True
		except OSError, ERR:
			logger.warn(u"Cannot remove {0}.".format(tmp_path));
		return ret

	def handle_downloaded_file(self, item, tmp_path, file_path):
		if not os.path.isfile(tmp_path):
			logger.error(u'{0} does not exist!'.format(tmp_path))
			return False

		if self.options.check_md5sum:
			md5sum = md5sum_file(tmp_path)
			logger.debug(u'ITEM MD5 sum {0}'.format(item[u'md5Checksum']))
			logger.debug(u'FILE MD5 sum {0}'.format(md5sum))
			if item[u'md5Checksum'] != md5sum:
				logger.error(u'Incorrect MD5 sum')
				self.handle_incorrect_downloaded_file(tmp_path)
				return False

		ret = False
		try:
			os.rename(tmp_path, file_path)
			ret = True
		except OSError, err:
			logger.warn(u"Cannot rename {0} to {1}.".format(item[u'title'], file_path));
		return ret

	def download_file(self, item, base_path = None):

		if base_path:
			file_path = os.sep.join([base_path.rstrip(os.sep), item[u'title']])
			if not os.path.exists(base_path):
				os.makedirs(base_path)
		else:
			file_path = os.sep.join([u'.', item[u'title']])

		if os.path.isfile(file_path):
			logger.info(u'{0} exists.'.format(file_path))
			if self.options.conflict_action == u'add':
				index = 1
				while os.path.isfile(u'{0}.{1}'.format(file_path, index)):
					index = index + 1
				new_path = u'{0}.{1}'.format(file_path, index)
				logger.info(u'save to {1}'.format(new_path))
				file_path = new_path
			elif self.options.conflict_action == u'skip':
				logger.info(u'skip it')
				return True
			elif self.options.conflict_action == u'skip_strict':
				md5sum = md5sum_file(file_path)
				logger.debug(u'ITEM MD5 sum {0}'.format(item[u'md5Checksum']))
				logger.debug(u'FILE MD5 sum {0}'.format(md5sum))
				if item[u'md5Checksum'] == md5sum:
					logger.info(u'MD5 checksum is the same, skip it')
					return True
				else:
					logger.info(u'MD5 checksum is different, replace it')

		logger.info(u'Donwloading a file: {0}'.format(item[u'title']))
		tmp_path = file_path + ".tmp"

		ret = False
		if self.service.download_file(item[u'id'], tmp_path, try_to_resume = self.options.try_to_resume):
			ret = self.handle_downloaded_file(item, tmp_path, file_path)
		else:
			self.handle_incorrect_downloaded_file(tmp_path)

		if ret:
			logger.info(u"Download {0} to {1} successfully.".format(item[u'title'], file_path))
		else:
			logger.error(u"Download {0} to {1} failed.".format(item[u'title'], file_path))

		return ret

	def download_folder(self, item, base_path = None):
		logger.info(u'Donwloading a folder: {0}'.format(item[u'title']))

		(dirs, files) = self.service.list(parent_id=item[u'id'])

		ret = True
		for f in files:
			ret = self.download_file(f, os.sep.join([base_path, item[u'title']]))
			if not ret:
				logger.error(u'Download a file failed, stop it.')
				break
		for d in dirs:
			ret = self.download_folder(d, os.sep.join([base_path, item[u'title']]))
			if not ret:
				logger.error(u'Download a folder failed, stop it.')
				break
		return ret

	def execute(self, options):

		logger.info(u"Processing DOWNLOAD")
		logger.debug(options)
		self.options = options

		base_path = options.output_folder.rstrip(os.sep)
		if not os.path.exists(base_path):
			os.makedirs(base_path)

		item = self.service.get_item_by_path(options.target)
		if item == None:
			return False

		ret = True
		if item[u'mimeType'] == GoogleDriveService.MIMETYPE_FOLDER:
			ret = self.download_folder(item, base_path)
		else:
			ret = self.download_file(item, base_path)
		return ret
