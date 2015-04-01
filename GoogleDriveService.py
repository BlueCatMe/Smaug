# coding=utf-8
#!/usr/bin/python

import os
import sys
import traceback
import logging

import httplib2
import pprint

import argparse

from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from oauth2client.client import *

from oauth2client.file import Storage

logger = logging.getLogger(__name__)

def exception_format(exc):
	return u"{0}({1})".format(
			type(exc).__name__,
			str(exc).decode(sys.getfilesystemencoding())
			);

class GoogleDriveService:

	# Check https://developers.google.com/drive/scopes for all available scopes
	OAUTH_SCOPE = u'https://www.googleapis.com/auth/drive'

	# Redirect URI for installed apps
	REDIRECT_URI = u'urn:ietf:wg:oauth:2.0:oob'

	MIMETYPE_BINARY = u'application/octet-stream'
	MIMETYPE_FOLDER = u'application/vnd.google-apps.folder'

	DEFAULT_CONFLICT_ACTION = u'skip'

	def __init__(self):
		self.data = []
		self.drive_service = None
		self.options = {
				u'request_new_credentials': False,
				u'conflict_action': GoogleDriveService.DEFAULT_CONFLICT_ACTION,
				u'remove_after_upload': False,
				u'move_to_backup_folder': None,
				u'move_skipped_file': False,
				}

	def authorize(self, json_path, cred_path = None):

		credentials = None

		if (not self.options[u'request_new_credentials']) and cred_path != None:
			storage = Storage(cred_path)
			credentials = storage.get()

		if credentials is None or credentials.invalid:
			logger.debug(u"Authorize Google Drive.")
			# Run through the OAuth flow and retrieve credentials
			flow = flow_from_clientsecrets(
					json_path,
					GoogleDriveService.OAUTH_SCOPE,
					redirect_uri = GoogleDriveService.REDIRECT_URI)
			authorize_url = flow.step1_get_authorize_url()
			print u'Go to the following link in your browser: ' + authorize_url
			code = raw_input(u'Enter verification code: ').strip()
			try:
				credentials = flow.step2_exchange(code)
			except FlowExchangeError, err:
				logger.error(u"flow step2 exchange failed!")
				logger.error(exception_format(err))
				credentials = None

		elif credentials.access_token_expired:
			logger.debug(u'Refresh Google credentials')
			credentials.refresh(httplib2.Http())

		else:
			logger.debug(u'Retrieve stored Google credentials')

		if credentials != None:
			# Create an httplib2.Http object and authorize it with our credentials
			http = httplib2.Http()
			http = credentials.authorize(http)

			self.drive_service = build(u'drive', u'v2', http=http)

			if cred_path != None:
				storage = Storage(cred_path)
				storage.put(credentials)


		return (self.drive_service != None)

	def delete_file_by_id(self, file_id):
		ret = True
		try:
			self.drive_service.files().delete(fileId=file_id).execute()
		except Exception, err:
			logger.warn(u'Delete file failed!')
			logger.warn(exception_format(err))
			ret = False
		return ret

	def handle_uploaded_file(self, file_path, base = None):
		if base == None:
			base = os.path.dirname(file_path)

		logger.info(u"Base: {0}".format(base))

		if self.options[u'move_to_backup_folder'] != None:
			relative_path = os.path.relpath(file_path, base)
			new_folder_path = os.path.join(self.options[u'move_to_backup_folder'], os.path.dirname(relative_path))

			if not os.path.exists(new_folder_path):
				os.makedirs(new_folder_path)
			try:
				os.rename(file_path, os.path.join(new_folder_path, os.path.basename(file_path)))
				logger.info(u"Move uploaded file {0} to {1}".format(file_path, new_folder_path))
			except WindowsError, err:
				logger.warn(u"Cannot move uploaded file {0} to {1}".format(file_path, new_folder_path))
				logger.warn(exception_format(err))

	def upload_file(self, file_path, base=None, mimetype=None, title=None, parent_id=None):
		logger.info(u"Uploading file: {0}".format(file_path))

		if title == None:
			title = os.path.basename(file_path)

		if base == None:
			base = os.path.dirname(file_path)

		logger.info(u"Base: {0}".format(base))

		files = self.get_file_by_title(title, parent_id=parent_id)

		if len(files) > 0:
			logger.info(u"There is {0} file(s) with the same title.".format(len(files)))
			if self.options[u'conflict_action'] == u'skip':
				logger.info(u"`{0}' exists, skip it.".format(title))
				if self.options[u'move_skipped_file']:
					self.handle_uploaded_file(file_path, base=base)
				return files[0]
			elif self.options[u'conflict_action'] == u'replace':
				logger.info(u"`{0}' exists, replace it.".format(title))
				for file in files:
					logger.info(u"Delete file: {0}".format(file[u'title']))
					self.delete_file_by_id(file[u'id'])

		if mimetype == None:
			mimetype = GoogleDriveService.MIMETYPE_BINARY

		# Insert a file
		media_body = MediaFileUpload(file_path,
				mimetype=mimetype,
				resumable=True)

		body = {
			u'title': title,
			u'mimeType': mimetype,
		}

		if parent_id != None:
			body[u"parents"] = [{u'id':parent_id}]

		file = None
		try:
			file = self.drive_service.files().insert(
					body=body,
					media_body=media_body,
					convert=False).execute()
		except Exception, err:
			logger.error(u"Upload `{0}' failed!".format(file_path))
			logger.error(exception_format(err))
			file = None

		if file != None:
			logger.info(u"Upload `{0}' finished.".format(file_path));
			self.handle_uploaded_file(file_path, base=base)

		return file

	def upload_folder(self, folder_path, parent_id=None, without_folders = False):
		logger.info(u"Uploading folder: {0}".format(folder_path))

		base = os.path.dirname(folder_path)

		# windows returns unicode filename with unicode path.
		for root, dirs, files in os.walk(folder_path):

			relative_path = os.path.relpath(root, base)

			if without_folders:
				parent = {u'id':parent_id}
			else:
				parent = self.get_folder_by_path(relative_path, parent_id)
				if parent == None:
					parent = self.mkdir(relative_path, parent_id)

			for file in files:
				self.upload_file(os.path.join(root, file), base=base, title=file, parent_id=parent[u'id'])

	def upload(self, path, remote_folder = None, without_folders = False):
		result = None
		parent_id = None

		if remote_folder != None:
			parent = self.mkdir(remote_folder.rstrip('/'))
			parent_id = parent[u'id']

		path = path.rstrip(os.sep)

		if os.path.exists(path):
			if os.path.isdir(path):
				result = self.upload_folder(path, parent_id=parent_id, without_folders=without_folders)
			elif os.path.isfile(path):
				result = self.upload_file(path, parent_id=parent_id)
			else:
				logger.error(u"Not a file and not a folder!")
		else:
			logger.error(u"{0} does not exist!".format(path))

		return result

	def mkdir(self, folder_path, parent_id = None):
		dir_id = None

		names = folder_path.rstrip(os.sep).split(os.sep)

		# remove root directory empty name or current directory name, '.'
		if names[0] in [u'.', u'']:
			del names[0]

		if parent_id == None:
			parent_item = {
					u'id'	: u'root',
					u'title': u'root'
					}
		else:
			parent_item = {
					u'id'	: parent_id,
					u'title': parent_id,
					}

		for name in names:
			query = u"title=\"{0}\" and mimeType=\"{1}\" and \"{2}\" in parents and trashed=false".format(name, GoogleDriveService.MIMETYPE_FOLDER, parent_item['id'])
			results = self.drive_service.files().list(q=query).execute()
			items = results[u'items']
			num = len(items)
			# create a folder
			if num == 0:
				body = {
						u"title": u"{0}".format(name),
						u"parents": [{u'id':parent_item[u'id']}],
						u"mimeType": GoogleDriveService.MIMETYPE_FOLDER,
						}
				parent_item = self.drive_service.files().insert(
						body=body, convert=False).execute()
				logger.info(u"Create folder: {0}".format(name))
			else:
				parent_item = items[0]

			if num > 1:
				logger.warn(u"Find multiple folder with the same title, `{0}'".format(name))

		return parent_item

	def get_file_by_title(self, title, parent_id = None):

		if parent_id == None:
			parent_item = {
					u'id'	: u'root',
					u'title': u'root'
					}
		else:
			parent_item = {
					u'id'	: parent_id,
					u'title': parent_id,
					}

		query = u"title=\"{0}\" and mimeType!=\"{1}\" and \"{2}\" in parents and trashed=false".format(
				title,
				GoogleDriveService.MIMETYPE_FOLDER,
				parent_item['id']
				)

		results = self.drive_service.files().list(q=query).execute()

		return results[u'items']


	def get_folder_by_path(self, folder_path, parent_id = None):

		names = folder_path.rstrip(os.sep).split(os.sep)

		# remove root directory empty name or current directory name, '.'
		if names[0] in [u'.', u'']:
			del names[0]

		if parent_id == None:
			parent_item = {
					u'id'	: u'root',
					u'title': u'root'
					}
		else:
			parent_item = {
					u'id'	: parent_id,
					u'title': parent_id,
					}
		# start from root
		for name in names:
			query = u"title=\"{0}\" and mimeType=\"{1}\" and \"{2}\" in parents and trashed=false".format(name, GoogleDriveService.MIMETYPE_FOLDER, parent_item['id'])
			results = self.drive_service.files().list(q=query).execute()
			items = results[u'items']
			num = len(items)
			if num == 0:
				logger.info(u"Cannot find `{0}'".format(name))
				parent_item = None
				break

			if num > 1:
				logger.warn(u"Find multiple folder with the same title, `{0}'".format(name))

			parent_item = items[0]

		return parent_item
