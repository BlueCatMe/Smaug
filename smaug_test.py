#!/usr/bin/python
# coding=utf-8

import os
import sys

def main(argv):

	# upload
	os.system("python smaug.py upload action --remote-folder upload/test --log-file test.upload.log")
	# list
	os.system("python smaug.py list /upload/test --log-file test.list.log")
	os.system("python smaug.py list /upload/test --long --log-file test.list.long.log")
	# show
	os.system("python smaug.py show root --log-file test.show.log")
	# download
	os.system("python smaug.py download /upload/test --output-folder test_download --log-file test.download.log")

if __name__ == u"__main__":
	main(sys.argv)

