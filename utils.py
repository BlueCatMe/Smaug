#!/usr/bin/python
# coding=utf-8
import os, sys
import hashlib

def md5sum_file(file_path):
	hash = hashlib.md5()
	with open(file_path) as f:
		for chunk in iter(lambda: f.read(4096), ""):
			hash.update(chunk)
	return hash.hexdigest()

# pyinstaller will cause os.getfilesystemencoding() return None.
# wrapper it into a function to return 'UTF-8' by default.
def getfilesystemencoding():
	encoding = sys.getfilesystemencoding()
	if encoding == None:
		encoding = u'UTF-8'
	return encoding
