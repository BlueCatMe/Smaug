# coding=utf-8
#!/usr/bin/python

import os
import sys
import logging

from utils import *

from GoogleDriveService import *

logger = logging.getLogger()

def main(argv):

	# translate encoding from file system to unicode.
	argv = [S2P(a) for a in argv]

	logging.basicConfig(level=logging.DEBUG)

	if not os.path.isfile(GoogleDriveService.CLIENT_SECRET_JSON_PATH):
		logger.critical("Please prepare %s for Google Drive API usage." % GoogleDriveService.CLIENT_SECRET_JSON_PATH)
		return -1

	parser = argparse.ArgumentParser(description='Batch upload files to Google Drive')
	parser.add_argument('target', nargs='?',
			help="target path, can be file or folder")
	parser.add_argument('--without-folders', action='store_true',
			default=False, help="Do not recreate folder structure in Google Drive.")
	parser.add_argument('--remove-after-upload', action='store_true',
			default=False, help="Remove uploaded file on disk.")
	parser.add_argument('--move-to-backup-folder', default=None,
			help="Move uploaded file to a backup folder.")
	parser.add_argument('--remote-folder', default=None,
			help="The remote folder path to upload the documents separated by '/'.")
	parser.add_argument('--conflict-action', default='skip', choices=['skip', 'replace', 'add'],
			help="How to handle existing file with the same title")
	parser.add_argument('--log-file', default=None,
			help="The remote folder path to upload the documents separated by '/'.")
	options = parser.parse_args(argv[1:])

	if options.log_file != None:
		file_handler = logging.FileHandler(options.log_file, mode = 'w')
		file_handler.setLevel(logging.DEBUG)
		file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		file_handler.setFormatter(file_formatter)
		logger.addHandler(file_handler)

	logger.debug(options)

	service = GoogleDriveService()

	service.options['conflict_action'] = options.conflict_action
	service.options['remove_after_upload'] = options.remove_after_upload
	service.options['move_to_backup_folder'] = options.move_to_backup_folder

	logger.debug(service.options)

	if options.move_to_backup_folder != None:
		if not os.path.exists(options.move_to_backup_folder):
			try:
				os.makedirs(options.move_to_backup_folder)
			except OSError, err:
				logger.critical("Cannot create backup folder `%s'" % options.move_to_backup_folder)
				return -1

		if not os.path.isdir(options.move_to_backup_folder):
			logger.critical("`%s' is not a folder." % options.move_to_backup_folder)
			return -1

	if service.authorize():
		service.upload(options.target,
				remote_folder=options.remote_folder,
				without_folders=options.without_folders)

if __name__ == "__main__":
	main(sys.argv)

