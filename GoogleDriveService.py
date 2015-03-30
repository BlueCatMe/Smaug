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

logger = logging.getLogger(__name__)

class GoogleDriveService:
	CLIENT_SECRET_JSON_PATH = 'client_secret.json'

	# Check https://developers.google.com/drive/scopes for all available scopes
	OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'

	# Redirect URI for installed apps
	REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

	MIMETYPE_BINARY = 'application/octet-stream'
	MIMETYPE_FOLDER = "application/vnd.google-apps.folder"

	DEFAULT_CONFLICT_ACTION = 'skip'

	def __init__(self):
		self.data = []
		self.drive_service = None
		self.options = {
				'conflict_action': GoogleDriveService.DEFAULT_CONFLICT_ACTION
				}

	def authorize(self):
		credentials = None
		logger.debug("Authorize Google Drive.")
		# Run through the OAuth flow and retrieve credentials
		flow = flow_from_clientsecrets(
				GoogleDriveService.CLIENT_SECRET_JSON_PATH,
				GoogleDriveService.OAUTH_SCOPE,
				redirect_uri = GoogleDriveService.REDIRECT_URI)
		authorize_url = flow.step1_get_authorize_url()
		print 'Go to the following link in your browser: ' + authorize_url
		code = raw_input('Enter verification code: ').strip()
		try:
			credentials = flow.step2_exchange(code)
		except FlowExchangeError, err:
			logger.error("flow step2 exchange failed! %s" % (err))
			credentials = None

		if credentials != None:
			# Create an httplib2.Http object and authorize it with our credentials
			http = httplib2.Http()
			http = credentials.authorize(http)

			self.drive_service = build('drive', 'v2', http=http)


		return (self.drive_service != None)

	def delete_file_by_id(self, file_id):
		ret = True
		try:
			self.drive_service.files().delete(fileId=file_id).execute()
		except Exception, error:
			logger.error('Delete file failed!')
			logger.error(traceback.format_exc())
			ret = False
		return ret

	def upload_file(self, file_path, mimetype=None, title=None, parent_id=None):
		logger.info("Uploading file: %s" % file_path);

		if title == None:
			title = os.path.basename(file_path)

		files = self.get_file_by_title(title, parent_id=parent_id)

		if len(files) > 0:
			logger.info("There is %d file(s) with the same title." % len(files))
			if self.options['conflict_action'] == 'skip':
				logger.info("`%s' exists, skip it." % (title))
				return files[0]
			elif self.options['conflict_action'] == 'replace':
				logger.info("`%s' exists, replace it." % (title))
				for file in files:
					logger.info("Delete file: %s" % file['title'])
					self.delete_file_by_id(file['id'])

		if mimetype == None:
			mimetype = GoogleDriveService.MIMETYPE_BINARY

		# Insert a file
		media_body = MediaFileUpload(file_path,
				mimetype=mimetype,
				resumable=True)

		body = {
			'title': title,
			'mimeType': mimetype,
		}

		if parent_id != None:
			body["parents"] = [{'id':parent_id}]

		file = None
		try:
			file = self.drive_service.files().insert(
					body=body,
					media_body=media_body,
					convert=False).execute()
		except Exception, err:
			logger.error("Upload `%s' failed!" % (file_path))
			logger.error(traceback.format_exc())
			pprint.pprint(file)
			file = None

		if file != None:
			logger.info("Upload `%s' finished." % (file_path));

		return file

	def upload_folder(self, folder_path, parent_id=None, without_folders = False):
		logger.info("Uploading folder: %s" % folder_path);

		for root, dirs, files in os.walk(folder_path):
			if without_folders:
				parent = {'id':parent_id}
			else:
				parent = self.get_folder_by_path(root, parent_id)
				if parent == None:
					parent = self.mkdir(root, parent_id)

			for file in files:
				self.upload_file(os.path.join(root, file), title=file, parent_id=parent['id'])

	def upload(self, path, remote_folder = None, without_folders = False):
		result = None
		parent_id = None

		if remote_folder != None:
			parent = self.mkdir(remote_folder)
			parent_id = parent['id']

		if os.path.exists(path):
			if os.path.isdir(path):
				result = self.upload_folder(path, parent_id, without_folders)
			elif os.path.isfile(path):
				result = self.upload_file(path, parent_id=parent_id)
			else:
				logger.error("Not a file and not a folder!")
		else:
			logger.error("%s does not exist!" % path)

		return result

	def mkdir(self, folder_path, parent_id = None):
		dir_id = None

		names = folder_path.rstrip(os.sep).split(os.sep)

		# remove root directory empty name or current directory name, '.'
		if names[0] in ['.', '']:
			del names[0]

		if parent_id == None:
			parent_item = {
					'id'	: 'root',
					'title'	: 'root'
					}
		else:
			parent_item = {
					'id'	: parent_id,
					'title'	: parent_id,
					}

		for name in names:
			query = "title=\"%s\" and mimeType=\"%s\" and \"%s\" in parents and trashed=false" % (name, GoogleDriveService.MIMETYPE_FOLDER, parent_item['id'])
			results = self.drive_service.files().list(q=query).execute()
			items = results['items']
			num = len(items)
			# create a folder
			if num == 0:
				body = {
						"title": name,
						"parents": [{'id':parent_item['id']}],
						"mimeType": GoogleDriveService.MIMETYPE_FOLDER,
						}
				parent_item = self.drive_service.files().insert(
						body=body, convert=False).execute()
				logger.info("Create folder: %s" % name)
			else:
				parent_item = items[0]

			if num > 1:
				logger.warn("Find multiple folder with the same title, `%s'" % name)

		return parent_item

	def get_file_by_title(self, title, parent_id = None):

		if parent_id == None:
			parent_item = {
					'id'	: 'root',
					'title'	: 'root'
					}
		else:
			parent_item = {
					'id'	: parent_id,
					'title'	: parent_id,
					}

		query = "title=\"%s\" and mimeType!=\"%s\" and \"%s\" in parents and trashed=false" % (
				title,
				GoogleDriveService.MIMETYPE_FOLDER,
				parent_item['id']
				)

		results = self.drive_service.files().list(q=query).execute()

		return results['items']


	def get_folder_by_path(self, folder_path, parent_id = None):

		names = folder_path.rstrip(os.sep).split(os.sep)

		# remove root directory empty name or current directory name, '.'
		if names[0] in ['.', '']:
			del names[0]

		if parent_id == None:
			parent_item = {
					'id'	: 'root',
					'title'	: 'root'
					}
		else:
			parent_item = {
					'id'	: parent_id,
					'title'	: parent_id,
					}
		# start from root
		for name in names:
			query = "title=\"%s\" and mimeType=\"%s\" and \"%s\" in parents and trashed=false" % (name, GoogleDriveService.MIMETYPE_FOLDER, parent_item['id'])
			results = self.drive_service.files().list(q=query).execute()
			items = results['items']
			num = len(items)
			if num == 0:
				logger.info("Cannot find `%s' folder in %s" % (name, parent_item['title']))
				parent_item = None
				break

			if num > 1:
				logger.warn("Find multiple folder with the same title, `%s'" % name)

			parent_item = items[0]

		return parent_item
