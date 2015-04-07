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
from apiclient import errors
from oauth2client.client import *

from oauth2client.file import Storage

logger = logging.getLogger(__name__)

def calculate_speed(start_time, progress, total_size, base = 1024):
	now = datetime.datetime.now()
	running_time = (datetime.datetime.now() - start_time).total_seconds()
	return int((total_size * progress / base) / running_time)


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

	TRANSFER_CHUNK_SIZE = 1024*1024

	CREDENTIALS_EXPIRE_IN_SECOND = 3600

	DEFAULT_CONFLICT_ACTION = u'skip'

	DEFAULT_UPLOAD_RETRY_COUNT = 3

	def __init__(self, json_path, cred_path):
		self.data = []
		# internal resources
		self.drive_service = None
		self.client_secret_json_path = json_path
		self.credentials_path = cred_path
		# dynamic variables
		self.credentials_refresh_time = None
		self.remote_base = ''
		self.remote_folder_data_cache = {}
		# class options
		self.options = {
				u'request_new_credentials': False,
				u'conflict_action': GoogleDriveService.DEFAULT_CONFLICT_ACTION,
				u'remove_after_upload': False,
				u'move_to_backup_folder': None,
				u'move_skipped_file': False,
				}

	def authorize_raw(self):

		credentials = None

		if (not self.options[u'request_new_credentials']) and self.credentials_path != None:
			storage = Storage(self.credentials_path)
			credentials = storage.get()

		if credentials is None or credentials.invalid:
			logger.debug(u"Authorize Google Drive.")
			# Run through the OAuth flow and retrieve credentials
			flow = flow_from_clientsecrets(
					self.client_secret_json_path,
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
			# Force refresh to known when it will expire.
			credentials.refresh(httplib2.Http())

		self.credentials_refresh_time = datetime.datetime.now()

		if credentials != None:
			# Create an httplib2.Http object and authorize it with our credentials
			http = httplib2.Http()
			http = credentials.authorize(http)

			self.drive_service = build(u'drive', u'v2', http=http)

			if self.credentials_path != None:
				storage = Storage(self.credentials_path)
				storage.put(credentials)


		return (self.drive_service != None)

	# call this function before any non-authorize drive API.
	def service_refresh(self):

		result = True

		do_refresh = False

		now = datetime.datetime.now()

		if self.credentials_refresh_time == None:
			do_refresh = True
		elif (now - self.credentials_refresh_time).total_seconds() > (GoogleDriveService.CREDENTIALS_EXPIRE_IN_SECOND * 0.9):
			do_refresh = True

		if do_refresh == True:
			result = self.authorize_raw()
			logger.info(u"Service Refresh Time: {0}".format(self.credentials_refresh_time))

		return result

	def authorize(self):
		return self.service_refresh()

	def delete_file_by_id(self, file_id):
		ret = True
		try:
			self.service_refresh()
			self.drive_service.files().delete(fileId=file_id).execute()
		except Exception, err:
			logger.warn(u'Delete file failed!')
			logger.warn(exception_format(err))
			ret = False
		return ret

	def handle_uploaded_file(self, file_path, base = None):
		if base == None:
			base = os.path.dirname(file_path)

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

	UPLOAD_SKIPPED		= 1
	UPLOAD_DONE		= 0
	UPLOAD_FAIL		= -1
	UPLOAD_SERVICE_ERROR	= -2

	def upload_file_raw(self, file_path, base=None, mimetype=None, title=None, parent_id=None):
		logger.info(u"Uploading file: {0}".format(file_path))

		if title == None:
			title = os.path.basename(file_path)

		if base == None:
			base = os.path.dirname(file_path)

		files = self.get_file_by_title(title, parent_id=parent_id)

		if len(files) > 0:
			logger.info(u"There is {0} file(s) with the same title.".format(len(files)))
			if self.options[u'conflict_action'] == u'skip':
				logger.info(u"`{0}' exists, skip it.".format(title))
				return (files[0], GoogleDriveService.UPLOAD_SKIPPED)
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
				chunksize=GoogleDriveService.TRANSFER_CHUNK_SIZE,
				resumable=True)

		body = {
			u'title': title,
			u'mimeType': mimetype,
		}

		if parent_id != None:
			body[u"parents"] = [{u'id':parent_id}]

		response = None
		progress = 0
		start_time = datetime.datetime.now()
		total_size = os.path.getsize(file_path)
		upload_return = GoogleDriveService.UPLOAD_FAIL
		try:
			self.service_refresh()
			if total_size == 0:
				response = self.drive_service.files().insert(
						body=body,
						media_body=None,
						convert=False).execute()
			else:
				request = self.drive_service.files().insert(
						body=body,
						media_body=media_body,
						convert=False)
				while response is None:
					status, response = request.next_chunk()
					if status:
						progress = status.progress()

						sys.stdout.write(u"Progress {0}% ({1}/{2} bytes, {3} KB/s)\r".format(
							int(progress * 100),
							int(total_size * progress),
							total_size,
							calculate_speed(start_time, progress, total_size))
							)
		except errors.HttpError, err:
			logger.warn(u"Only {0}/{1} bytes are transferred ({2} KB/s).".format(
				int(total_size * progress),
				total_size,
				calculate_speed(start_time, progress, total_size))
				)
			if err.resp.status in [400, 500, 502, 503]:
				logger.warn(u"Google Service error with status code {0}!".format(err.resp.status))
				upload_return = GoogleDriveService.UPLOAD_SERVICE_ERROR
			logger.error(u"Upload `{0}' to `{1}/{2}' failed!".format(file_path,
				self.remote_base,
				os.path.relpath(file_path, base).replace(os.sep, '/')
				))
			logger.error(exception_format(err))
			response = None
		except Exception, err:
			logger.error(u"Only {0}/{1} bytes are transferred ({2} KB/s).".format(
				int(total_size * progress),
				total_size,
				calculate_speed(start_time, progress, total_size))
				)
			logger.error(u"Upload `{0}' to `{1}/{2}' failed!".format(file_path,
				self.remote_base,
				os.path.relpath(file_path, base).replace(os.sep, '/')
				))
			logger.error(exception_format(err))
			response = None

		if response != None:
			logger.info(u"{0} bytes are transferred ({1} KB/s).".format(
				total_size,
				calculate_speed(start_time, 1, total_size))
				)
			logger.info(u"Upload `{0}' to `{1}/{2}' finished.".format(file_path,
				self.remote_base,
				os.path.relpath(file_path, base).replace(os.sep, '/')
				))
			upload_return = GoogleDriveService.UPLOAD_DONE

		return (response, upload_return)

	def upload_file(self, file_path, base=None, mimetype=None, title=None, parent_id=None):
		retry_count = GoogleDriveService.DEFAULT_UPLOAD_RETRY_COUNT
		while retry_count > 0:
			(f, r) = self.upload_file_raw(file_path, base=base, mimetype=mimetype, title=title, parent_id=parent_id)
			if f != None: # uploaded or skipped
				if (r == GoogleDriveService.UPLOAD_DONE) or (r == GoogleDriveService.UPLOAD_SKIPPED and self.options[u'move_skipped_file']):
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
				parent = {u'id':parent_id}
			else:
				parent = self.mkdir(relative_path, parent_id)

			for file in files:
				(f, result) = self.upload_file(os.path.join(root, file), base=base, title=file, parent_id=parent[u'id'])
				if f == None:
					folder_result = False

		return folder_result

	def upload(self, path, remote_folder = None, without_folders = False):

		result = False
		parent_id = None

		if remote_folder != None:
			parent = self.mkdir(remote_folder.rstrip('/'))
			parent_id = parent[u'id']
			self.remote_base = remote_folder

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

	def mkdir(self, folder_path, parent_id = None):
		dir_id = None

		folder_path = folder_path.rstrip(os.sep)
		parent_folder_path = os.path.dirname(folder_path)
		if parent_folder_path in self.remote_folder_data_cache:
			logger.debug(u"`{0}' id query is cached hit.".format(parent_folder_path))
			parent_id = self.remote_folder_data_cache[parent_folder_path]['id']
			names = os.path.relpath(folder_path, parent_folder_path).split(os.sep)
		else:
			names = folder_path.split(os.sep)

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
			self.service_refresh()
			query = u'trashed=false'
			query += u' and title=\"{0}\"'.format(name)
			query += u' and mimeType=\"{0}\"'.format(GoogleDriveService.MIMETYPE_FOLDER)
			query += u' and \"{0}\" in parents'.format(parent_item['id'])
			results = self.drive_service.files().list(q=query).execute()
			items = results[u'items']
			num = len(items)
			# create a folder
			if num == 0:
				self.service_refresh()
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

		if parent_item != None:
			self.remote_folder_data_cache[folder_path] = parent_item

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

		query = u'trashed=false'
		query += u' and title=\"{0}\"'.format(title)
		query += u' and mimeType!=\"{0}\"'.format(GoogleDriveService.MIMETYPE_FOLDER)
		query += u' and \"{0}\" in parents'.format(parent_item['id'])

		self.service_refresh()
		results = self.drive_service.files().list(q=query).execute()

		return results[u'items']


	def get_folder_by_path(self, folder_path, parent_id = None):

		folder_path = folder_path.rstrip(os.sep)

		parent_folder_path = os.path.dirname(folder_path)
		if parent_folder_path in self.remote_folder_data_cache:
			logger.debug(u"`{0}' id query is cached hit.".format(parent_folder_path))
			parent_id = self.remote_folder_data_cache[parent_folder_path]['id']
			names = os.path.relpath(folder_path, parent_folder_path).split(os.sep)
		else:
			names = folder_path.split(os.sep)

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
			self.service_refresh()
			query = u'trashed=false'
			query += u' and title=\"{0}\"'.format(name)
			query += u' and mimeType=\"{0}\"'.format(GoogleDriveService.MIMETYPE_FOLDER)
			query += u' and \"{0}\" in parents'.format(parent_item['id'])
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

		if parent_item != None:
			self.remote_folder_data_cache[folder_path] = parent_item

		return parent_item
