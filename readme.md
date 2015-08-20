# Smaug v2.0#

A command line interface to upload/download buck files and folders.
This tool support list, upload, and download files for Google Drive.
File synchronization will not be supported.

## Features ##

* upload files or folders to assigned GoogleDrive path.
 * move uploaded files to another location.
 * support different conflict action to handle files with the same name.
* download files from GoogleDrive, especially for very big files.
 * skip downloaded files.
 * resume interrupted download files.

## Requirement ##

1. Enable Drive API and apply client id in Google Developers Console.
   Download client json file and rename it to client_secret.json.
   Please refer [Quickstart: Run a Drive App in Python][quickstart]

2. Install the Gogole Clinent Library.
   To install the Google API Python Client on a system, you must use either the pip command or easy_install command.
   * easy_install --upgrade google-api-python-client
   * pip install --upgrade google-api-python-client

3. Install required packages.
   * easy_install --upgrade install python-dateutil
   * pip install --upgrade python-dateutil

[quickstart]: https://developers.google.com/drive/web/quickstart/quickstart-python

## Getting Started ##

It will show an URL and ask an OAuth2 token for accessing Google Drive at the first launch. Go to shown url in a browser, log into your Google account to grant permission and copy code to console. It will store your credentials in the script folder by default so that your only need to do this step once.

## Usasge ##

	usage: smaug.py [-h] [--request-new-credentials]
	               [--credentials-path CREDENTIALS_PATH]
	               [--client-secret-json-path CLIENT_SECRET_JSON_PATH]
	               [--log-file LOG_FILE]
	               {upload,download,list} target

	GoogleDrive CLI "Smaug"

	positional arguments:
	  {upload,download,list}
	                        what action to do: what action to do: upload,download,list
	  target                target path, can be files or folders

	common optional arguments:
	  -h, --help            show this help message and exit
	  --request-new-credentials
	                        Request new credentials to change account.
	  --credentials-path CREDENTIALS_PATH
	                        assign credentials file path.
	  --client-secret-json-path CLIENT_SECRET_JSON_PATH
	                        assign client secret json file path.
	  --log-file LOG_FILE   The remote folder path to upload the documents
	                        separated by '/'.

	ls optional arguments:
	  --long                Use a long listing format.

	upload optional arguments:
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

	download optional arguments:
	  --output-folder OUTPUT_FOLDER
				The local folder path to store downloaded files
				separated by '/'.
	  --check-md5sum        Check downloaded file md5 sum.
	  --remove-incorrect-download
				Remove incorrect downloaded files.
	  --conflict-action {skip,add,skip_strict}
				How to handle existing file with the same title
	  --try-to-resume       Try to resume interrupted download.


### List Example ###

List root of Google Drive

	% python smaug.py list /

List /Documents/MyReport in details

	% python smaug.py list /Documents/MyReport --long

### Upload Example ###

If there are files with name the same as uploaded one on GoogleDrive, it will be skipped by default.

	% python smaug.py upload FILE

upload FILE to GoogleDrive root

	% python smaug.py upload DIR
	
upload DIR to GoogleDrive root, tree structure of DIR will be preserved.

	% python upload --remote-folder upload/new FILE1 FILE2 DIR

upload FILE1, FILE2, and DIR to GoogleDrive:/upload/new.

	% python upload --move-to-backup-folder file.uploaded --conflict-action replace FILES DIRS

upload FILES and DIRS to GoogleDrive:/, if there are files with name the same as uploaded one on GoogleDrive, they will be deleted first. After a file is uploaded, it will be moved to file.uploaded folder from original location.

	% python upload --move-to-backup-folder file.uploaded --move-skipped-file FILES DIRS

upload FILES and DIRS to GoogleDrive:/. Even a skipped file will be moved to backup folder.

### Download Example ###

Download a file or directory from GoogleDrive. If there is a file with the same name exists, it will be replaced by default.

	% python smaug.py download /path/to/file

Download a file or directory from GoogleDrive and save to another location.

	% python smaug.py download /path/to/file --output-folder /path/for/store

Download a file or directory from GoogleDrive. If there is a file with the same name exists, skip this download.

	% python smaug.py download /path/to/file --output-folder /path/for/store --conflict-action skip

Download a file or directory from GoogleDrive. If there is a file with the same name exists, skip this download only the MD5 checksum of existing file is the same as of GoogleDrive file.

	% python smaug.py download /path/to/file --output-folder /path/for/store --conflict-action skip_strict

