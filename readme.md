# Google Drive Uploader #

A command line interface to upload buck files and folders.

## Requirement ##

1. Enable Drive API and apply client id in Google Developers Console.
   Download client json file and rename it to client_secret.json.
   Please refer [Quickstart: Run a Drive App in Python][quickstart]

2. Install the Gogole Clinent Library.
   To install the Google API Python Client on a system, you must use either the pip command or easy_install command.
   * easy_install --upgrade google-api-python-client
   * pip install --upgrade google-api-python-client

[quickstart]: https://developers.google.com/drive/web/quickstart/quickstart-python

## Usasge ##

	usage: main.py [-h] [--without-folders]
		       [--move-to-backup-folder MOVE_TO_BACKUP_FOLDER]
		       [--move-skipped-file] [--remote-folder REMOTE_FOLDER]
		       [--conflict-action {skip,replace,add}] [--log-file LOG_FILE]
		       [target]

	Batch upload files to Google Drive

	positional arguments:
	  target                target path, can be file or folder

	optional arguments:
	  -h, --help            show this help message and exit
	  --without-folders     Do not recreate folder structure in Google Drive.
	  --move-to-backup-folder MOVE_TO_BACKUP_FOLDER
				Move uploaded file to a backup folder.
	  --move-skipped-file   Move skipped files to backup folder. This option must
				work with --move-to-backup-folder
	  --remote-folder REMOTE_FOLDER
				The remote folder path to upload the documents
				separated by '/'.
	  --conflict-action {skip,replace,add}
				How to handle existing file with the same title
	  --log-file LOG_FILE   The remote folder path to upload the documents
				separated by '/'.

