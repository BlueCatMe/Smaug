# coding=utf-8
#!/usr/bin/python

import sys

GLOBAL_ENCODING = 'utf-8'

def S2U(str):
	return str.decode(sys.getfilesystemencoding())

def P2U(str):
	return str.decode(GLOBAL_ENCODING)

def U2P(str):
	return str.encode(GLOBAL_ENCODING)

def S2P(str):
	return U2P(S2U(str))
