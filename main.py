# coding=utf-8
#!/usr/bin/python

import os
import sys
import logging

from GoogleDriveService import *

logger = logging.getLogger()

CLIENT_SECRET_JSON_FILENAME = u'client_secret.json'
CREDENTIALS_STORAGE_FILENAME = u'default.cred'

def main(argv):

	# translate encoding from file system to unicode.
	argv = [a.decode(sys.getfilesystemencoding()) for a in argv]

	logging.basicConfig(level=logging.DEBUG)

	client_secret_json_path = os.path.join(os.path.dirname(argv[0]), CLIENT_SECRET_JSON_FILENAME)
	credentials_storage_path = os.path.join(os.path.dirname(argv[0]), CREDENTIALS_STORAGE_FILENAME)

	if not os.path.isfile(client_secret_json_path):
		logger.critical(u"Please prepare %s for Google Drive API usage." % CLIENT_SECRET_JSON_FILENAME)
		return -1

	parser = argparse.ArgumentParser(description=u'Batch upload files to Google Drive')
	parser.add_argument(u'targets', nargs=u'+',
			help=u"target path, can be files or folders")
	parser.add_argument(u'--without-folders', action='store_true',
			default=False, help=u"Do not recreate folder structure in Google Drive.")
	parser.add_argument(u'--request-new-credentials', action='store_true',
			default=False, help=u"Request new credentials to change account.")
	parser.add_argument(u'--credentials-path', default=credentials_storage_path,
			help=u"assign credentials file path.")
	parser.add_argument(u'--move-to-backup-folder', default=None,
			help=u"Move uploaded file to a backup folder.")
	parser.add_argument(u'--move-skipped-file', action=u'store_true',
			default=False, help=u"Move skipped files to backup folder. This option must work with --move-to-backup-folder")
	parser.add_argument(u'--remote-folder', default=None,
			help=u"The remote folder path to upload the documents separated by '/'.")
	parser.add_argument(u'--conflict-action', default=u'skip', choices=[u'skip', u'replace', u'add'],
			help=u"How to handle existing file with the same title")
	parser.add_argument(u'--log-file', default=None,
			help=u"The remote folder path to upload the documents separated by '/'.")
	options = parser.parse_args(argv[1:])

	if options.log_file != None:
		file_handler = logging.FileHandler(options.log_file, mode = u'w', encoding = u'utf-8')
		file_handler.setLevel(logging.DEBUG)
		file_formatter = logging.Formatter(u'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		file_handler.setFormatter(file_formatter)
		logger.addHandler(file_handler)

	logger.debug(options)

	credentials_storage_path = options.credentials_path

	service = GoogleDriveService()

	service.options[u'request_new_credentials'] = options.request_new_credentials
	service.options[u'conflict_action'] = options.conflict_action
	service.options[u'move_to_backup_folder'] = options.move_to_backup_folder
	service.options[u'move_skipped_file'] = options.move_skipped_file

	logger.debug(service.options)

	if options.move_to_backup_folder != None:
		if not os.path.exists(options.move_to_backup_folder):
			try:
				os.makedirs(options.move_to_backup_folder)
			except OSError, err:
				logger.critical(u"Cannot create backup folder `%s'" % options.move_to_backup_folder)
				return -1

		if not os.path.isdir(options.move_to_backup_folder):
			logger.critical(u"`%s' is not a folder." % options.move_to_backup_folder)
			return -1

	if service.authorize(client_secret_json_path, credentials_storage_path):
		for target in options.targets:
			result = service.upload(target,
				remote_folder=options.remote_folder,
				without_folders=options.without_folders)
			if result == True:
				logger.info(u"Uploading `{0}' successed.".format(target));
			else:
				logger.warn(u"Uploading `{0}' failed.".format(target));

if __name__ == u"__main__":
	main(sys.argv)

