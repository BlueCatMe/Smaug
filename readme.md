# Google Drive Uploader #

A command line interface to upload buck files and folders.
This tool focuses on uploading functions.
File synchronization or data download will not be supported.

Features
* upload files or folders to assigned GoogleDrive path.
* move uploaded files to another location.
* support different conflict action to handle files with the same name.

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

	usage: main.py [-h] [--without-folders] [--request-new-credentials]
	               [--credentials-path CREDENTIALS_PATH]
	               [--move-to-backup-folder MOVE_TO_BACKUP_FOLDER]
	               [--move-skipped-file] [--remote-folder REMOTE_FOLDER]
	               [--conflict-action {skip,replace,add}] [--log-file LOG_FILE]
	               targets [targets ...]

	Batch upload files to Google Drive

	positional arguments:
	  targets               target path, can be files or folders

	optional arguments:
	  -h, --help            show this help message and exit
	  --without-folders     Do not recreate folder structure in Google Drive.
          --request-new-credentials
          			Request new credentials to change account.
          --credentials-path CREDENTIALS_PATH
				assign credentials file path.
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

## Getting Started ##

It will show an URL and ask an OAuth2 token for accessing Google Drive at the first launch. Go to shown url in a browser, log into your Google account to grant permission and copy code to console. It will store your credentials in the script folder by default so that your only need to do this step once.

If there are files with name the same as uploaded one on GoogleDrive, it will be skipped by default

	% python main.py FILE

upload FILE to GoogleDrive root

	% python main.py DIR
	
upload DIR to GoogleDrive root, tree structure of DIR will be preserved.

	% python --remote-folder upload/new FILE1 FILE2 DIR

upload FILE1, FILE2, and DIR to GoogleDrive:/newly_upload/new.

	% python --move-to-backup-folder file.uploaded --conflict-action replace FILES DIRS

upload FILES and DIRS to GoogleDrive:/, if there are files with name the same as uploaded one on GoogleDrive, they will be deleted first. After a file is uploaded, it will be moved to file.uploaded folder from original location.

	% python --move-to-backup-folder file.uploaded --move-skipped-file FILES DIRS

upload FILES and DIRS to GoogleDrive:/. Even a skipped file will be moved to backup folder.
