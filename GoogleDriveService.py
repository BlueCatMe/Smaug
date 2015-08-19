# coding=utf-8
#!/usr/bin/python

import os
import sys
import re
import traceback
import logging

import httplib2
import httplib
import pprint

import argparse

from apiclient.discovery import build
from apiclient.http import MediaFileUpload, MediaIoBaseDownload
from apiclient import errors
from oauth2client.client import *

from oauth2client.file import Storage

from utils import getfilesystemencoding

logger = logging.getLogger(__name__)

def calculate_speed(start_time, progress, total_size, base = 1024):
	now = datetime.datetime.now()
	running_time = (datetime.datetime.now() - start_time).total_seconds()
	return int((total_size * progress / base) / running_time)


def exception_format(exc):
	return u"{0}({1})".format(
			type(exc).__name__,
			str(exc).decode(getfilesystemencoding())
			);

def make_parent_item(item_id = None):
	# default is root
	item = {
		u'id'	: u'root',
		u'title': u'root'
		}

	if item_id != None:
		item = {
			u'id'	: item_id,
			u'title': item_id,
			}
	return item


class GoogleDriveService:

	# Check https://developers.google.com/drive/scopes for all available scopes
	OAUTH_SCOPE = u'https://www.googleapis.com/auth/drive'

	# Redirect URI for installed apps
	REDIRECT_URI = u'urn:ietf:wg:oauth:2.0:oob'

	MIMETYPE_BINARY = u'application/octet-stream'
	MIMETYPE_FOLDER = u'application/vnd.google-apps.folder'
	# for non-folder query
	MIMETYPE_NON_FOLDER = u'anything_not_folder'

	UPLOAD_TRANSFER_CHUNK_SIZE = 10*1024*1024
	DOWNLOAD_TRANSFER_CHUNK_SIZE = 10*1024*1024

	CREDENTIALS_EXPIRE_IN_SECOND = 3600

	DEFAULT_CONFLICT_ACTION = u'skip'

	DEFAULT_UPLOAD_RETRY_COUNT = 3

	DEFAULT_DOWNLOAD_RETRY_COUNT = 3

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

	def delete(self, file_id):
		ret = True
		try:
			self.service_refresh()
			self.drive_service.files().delete(fileId=file_id).execute()
		except Exception, err:
			logger.warn(u'Delete file failed!')
			logger.warn(exception_format(err))
			ret = False
		return ret

	def get(self, id):

		self.service_refresh()

		item = None
		try:
			item = self.drive_service.files().get(fileId=id).execute()
		except errors.HttpError, error:
			logger.error(u'Http Error: {0}'.format(error))

		return item

	def get_gdrive_items(self, title = None, parent_id = None, mimeType = None, trashed = False):

		self.service_refresh()

		if trashed:
			query = u'trashed=true'
		else:
			query = u'trashed=false'

		if bool(title):
			query += u' and title=\"{0}\"'.format(title)

		if mimeType == GoogleDriveService.MIMETYPE_NON_FOLDER:
			query += u' and mimeType!=\"{0}\"'.format(GoogleDriveService.MIMETYPE_FOLDER)
		elif mimeType != None:
			query += u' and mimeType=\"{0}\"'.format(mimeType)

		if parent_id != None:
			query += u' and \"{0}\" in parents'.format(parent_id)

		results = self.drive_service.files().list(q=query).execute()
		items = results[u'items']
		num = len(items)
		if bool(title) and num > 1:
			logger.warn(u"Find {0} items with the same title, `{1}'".format(num, title))

		return items


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

		items = self.get_gdrive_items(title = title, parent_id = parent_id, mimeType = GoogleDriveService.MIMETYPE_NON_FOLDER);

		if len(files) > 0:
			logger.info(u"There is {0} file(s) with the same title.".format(len(files)))
			if self.options[u'conflict_action'] == u'skip':
				logger.info(u"`{0}' exists, skip it.".format(title))
				return (files[0], GoogleDriveService.UPLOAD_SKIPPED)
			elif self.options[u'conflict_action'] == u'replace':
				logger.info(u"`{0}' exists, replace it.".format(title))
				for file in files:
					logger.info(u"Delete file: {0}".format(file[u'title']))
					self.delete(file[u'id'])

		if mimetype == None:
			mimetype = GoogleDriveService.MIMETYPE_BINARY

		# Insert a file
		media_body = MediaFileUpload(file_path,
				mimetype=mimetype,
				chunksize=GoogleDriveService.UPLOAD_TRANSFER_CHUNK_SIZE,
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
						sys.stdout.flush()
		except errors.HttpError, err:
			logger.error(u"Only {0}/{1} bytes are transferred ({2} KB/s).".format(
				int(total_size * progress),
				total_size,
				calculate_speed(start_time, progress, total_size))
				)
			if int(err.resp.status/100) == 5:
				upload_return = GoogleDriveService.UPLOAD_SERVICE_ERROR
			logger.error(u"Upload `{0}' to `{1}/{2}' failed!".format(file_path,
				self.remote_base,
				os.path.relpath(file_path, base).replace(os.sep, u'/')
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
				os.path.relpath(file_path, base).replace(os.sep, u'/')
				))
			logger.error(exception_format(err))
			response = None
		else:
			logger.info(u"{0} bytes are transferred ({1} KB/s).".format(
				total_size,
				calculate_speed(start_time, 1, total_size))
				)
			logger.info(u"Upload `{0}' to `{1}/{2}' finished.".format(file_path,
				self.remote_base,
				os.path.relpath(file_path, base).replace(os.sep, u'/')
				))
			upload_return = GoogleDriveService.UPLOAD_DONE

		if response:
			logger.info(u'Total {0} bytes are uploaded.'.format(total_size))

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

	def list(self, path = None, parent_id = None):

		parent_item = make_parent_item(parent_id);

		if path != None:
			logger.debug(u"List {0}".format(path));

			names = path.split(u'/')

			# remove root directory empty name or current directory name, '.'
			if names[0] in [u'.', u'']:
				del names[0]

			# get the last name to later process.
			target = names.pop()

			# check parent path first to get parent id.
			found_names = []
			for i in range(0, len(names)):
				name = names[i]
				items = self.get_gdrive_items(title = name, parent_id = parent_item[u'id'], mimeType = GoogleDriveService.MIMETYPE_FOLDER);
				if len(items) > 0:
					parent_item = items[0]
					found_names.append(name)
				else:
					logger.info(u"Cannot find `{0}' in `{1}'".format(name, u'/'.join(found_names)))
					return ([], [])

			logger.info(u'target = {0}'.format(target))
			# ls /xxx/yyy/zzz, check zzz is a folder or a file.
			if bool(target):
				items = self.get_gdrive_items(title = target, parent_id = parent_item[u'id']);
				if len(items) > 0:
					item = items[0]

					# target is a folder, list it again.
					if item[u'mimeType'] == GoogleDriveService.MIMETYPE_FOLDER:
						logger.info(u'Target {0} is a folder, list it again'.format(target))
						parent_item = item;
						found_names.append(target)

						items = self.get_gdrive_items(parent_id = parent_item[u'id']);
				else:
					logger.info(u"Cannot find `{0}' in `{1}'".format(target, u'/'.join(found_names)))
					return ([], [])
			# ls /xxx/yyy/zzz/, treat zzz as a folder.
			else:
				logger.debug(u'List a folder')
				items = self.get_gdrive_items(parent_id = parent_item[u'id']);
		else:
			logger.debug(u'List items with parent id')
			items = self.get_gdrive_items(parent_id = parent_item[u'id']);

		dirs = []
		files = []
		for item in items:
			if item[u'mimeType'] == GoogleDriveService.MIMETYPE_FOLDER:
				dirs.append(item)
			else:
				files.append(item)

		return (dirs,files)

	def upload(self, path, remote_folder = None, without_folders = False):

		result = False
		parent_id = None

		if remote_folder != None:
			parent = self.mkdir(remote_folder.rstrip(u'/'))
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

		folder_path = folder_path.rstrip(u'/')
		parent_folder_path = os.path.dirname(folder_path)
		if parent_folder_path in self.remote_folder_data_cache:
			logger.debug(u"`{0}' id query is cached hit.".format(parent_folder_path))
			parent_id = self.remote_folder_data_cache[parent_folder_path][u'id']
			names = os.path.relpath(folder_path, parent_folder_path).split(u'/')
		else:
			names = folder_path.split(u'/')

		# remove root directory empty name or current directory name, '.'
		if names[0] in [u'.', u'']:
			del names[0]

		parent_item = make_parent_item(parent_id);

		for name in names:
			self.service_refresh()
			items = self.get_gdrive_items(title = name, parent_id = parent_item[u'id'], mimeType = GoogleDriveService.MIMETYPE_FOLDER);
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

		if parent_item != None:
			self.remote_folder_data_cache[folder_path] = parent_item

		return parent_item

	def get_item_by_path(self, path, parent_id = None):

		path = path.rstrip(u'/')

		if path in self.remote_folder_data_cache:
			logger.debug(u"`{0}' query is cached hit.".format(path))
			return self.remote_folder_data_cache;
		else:
			names = path.split(u'/')

		# remove root directory empty name or current directory name, '.'
		if names[0] in [u'.', u'']:
			del names[0]

		parent_item = make_parent_item(parent_id);

		# start from root
		found_names = []
		found_item = None
		while len(names) > 0:
			name = names.pop(0)
			self.service_refresh()
			items = self.get_gdrive_items(title = name, parent_id = parent_item[u'id']);
			num = len(items)
			if num == 0:
				logger.info(u"Cannot find `{0}'".format(name))
				parent_item = None
				break

			parent_item = items[0]

		if parent_item != None:
			self.remote_folder_data_cache[path] = parent_item

		return parent_item

	def download_file_chunk(self, file_id, file_path):

		item = self.get(file_id)
		if item == None:
			return None

		fd = open(file_path, u'w')

		request = self.drive_service.files().get_media(fileId=file_id)
		media_request = MediaIoBaseDownload(fd, request, chunksize=GoogleDriveService.DOWNLOAD_TRANSFER_CHUNK_SIZE)

		start_time = datetime.datetime.now()
		total_size = int(item[u'fileSize'])
		while True:
			try:
				download_progress, done = media_request.next_chunk()
			except errors.HttpError, error:
				logger.error(u'Http Error: {0}'.format(error))
				return

			if download_progress:
				progress = download_progress.progress()
				sys.stdout.write(u"Progress {0}% ({1}/{2} bytes, {3} KB/s)\r".format(
							int(progress * 100),
							int(total_size * progress),
							total_size,
							calculate_speed(start_time, progress, total_size))
							)
				sys.stdout.flush()
			if done:
				break
				logger.info(u'Download Complete')
		return

	def download_file(self, file_id, file_path, try_to_resume = False):

		ret = True

		item = self.get(file_id)
		if item == None:
			return False

		download_url = item.get(u'downloadUrl')
		if download_url:

			start_time = datetime.datetime.now()
			total_size = int(item[u'fileSize'])
			retry = GoogleDriveService.DEFAULT_DOWNLOAD_RETRY_COUNT

			if try_to_resume and os.path.isfile(file_path):
				f = open(file_path, u'ab')
				downloaded_size = os.path.getsize(file_path)
			else:
				f = open(file_path, u'wb')
				downloaded_size = 0
			while downloaded_size < total_size:
				self.service_refresh()

				start_byte = downloaded_size
				end_byte = downloaded_size + GoogleDriveService.DOWNLOAD_TRANSFER_CHUNK_SIZE -1
				if total_size - downloaded_size < GoogleDriveService.DOWNLOAD_TRANSFER_CHUNK_SIZE:
					end_byte = downloaded_size + (total_size - downloaded_size) - 1

				resp = None
				content = None
				try:
					resp, content = self.drive_service._http.request(download_url,
						headers = {u'Range': u'bytes={0}-{1}'.format(start_byte, end_byte)})
				except httplib.IncompleteRead, err:
					logger.warn(u'IncompleteRead Exception: {0}'.format(err))
					resp = None

				if resp == None:
					logger.warn(u'HTTP request error')

				elif resp.status == 200:
					f.write(content)
					downloaded_size = int(resp[u'content-length'])
					break

				elif resp.status == 206:
					downloaded_chunk_size = None
					if u'content-length' in resp:
						downloaded_chunk_size = int(resp[u'content-length'])
					# Ex: 'content-range': 'bytes 10485760-20971519/27771630'
					elif u'content-range' in resp:
						range_data = re.split('[ -/]', resp[u'content-range'])
						downloaded_chunk_size = int(range_data[2]) - int(range_data[1]) + 1

					f.write(content)
					downloaded_size += downloaded_chunk_size

					progress = float(downloaded_size)/total_size
					sys.stdout.write(u"Progress {0}% ({1}/{2} bytes, {3} KB/s)\r".format(
								int(progress * 100),
								int(total_size * progress),
								total_size,
								calculate_speed(start_time, progress, total_size))
								)
					sys.stdout.flush()

					retry = GoogleDriveService.DEFAULT_DOWNLOAD_RETRY_COUNT
					continue

				else:
					logger.warn(u'An error occurred: {0}'.format(resp))

				# Only fail case go here!
				retry = retry - 1
				logger.warn(u'Download byte {0} - {1} failed. Remaining retry count: {2}'.format(start_byte, end_byte, retry))
				if retry == 0:
					logger.error(u'Retry over {0} times, give up'.format(GoogleDriveService.DEFAULT_DOWNLOAD_RETRY_COUNT))
					ret = False
					break
			f.close()
			if downloaded_size != total_size:
				logger.error("Downloaded size, {0} bytes, does not match total size, {1} bytes".format(downloaded_size, total_size))
				ret = False
			elif (os.stat(file_path).st_size != total_size):
				logger.error("Written size, {0} bytes, does not match total size, {1} bytes".format(os.stat(file_path).st_size, total_size))
				ret = False
			else:
				logger.info(u'Total {0}/{0} bytes are downloaded.'.format(downloaded_size, total_size))
		else:
			logger.error(u'The file doesn\'t have any content stored on Drive.');
			ret = False

		return ret
