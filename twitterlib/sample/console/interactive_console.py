#! /usr/bin/python2.6
# coding: utf-8
#
# simple twitter client
#

import sys
import os
import twitterlib

def main():
    if len(sys.argv) < 3:
        print 'usage: %s consumer_key consumer_secret' % __file__
        return
    key = sys.argv[1]
    sec = sys.argv[2]
    api = twitterlib.API(twitterlib.TwitterOAuth(key, sec))
    api.auth()
    import code
    code.InteractiveConsole(locals()).interact()

if __name__ == '__main__':
    main()
