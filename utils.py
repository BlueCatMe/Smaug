# coding=utf-8
#!/usr/bin/python

import sys

GLOBAL_ENCODING = 'utf-8'

def S2U(str):
	return str.decode(sys.getfilesystemencoding())

def S2P(str):
	return S2U(str).encode(GLOBAL_ENCODING)

def P2U(str):
	return str.decode(GLOBAL_ENCODING)

def P2S(str):
	return P2U(str).encode(sys.getfilesystemencoding())

