#!/usr/bin/env python3

from os import chdir, path
from optparse import OptionParser

from bottle import run
from buildhck import buildhck

def main():
    '''main method'''
    parser = OptionParser()
    parser.add_option('-s', '--server', dest='server',
                      help='bottle.py WSGI server backend')
    parser.add_option('-p', '--port', dest='port',
                      help='server port')
    parser.add_option('-b', '--buildsdir', dest='builds_directory',
                      help='directory for builds')
    optargs = parser.parse_args()

    for key in buildhck.SETTINGS.keys():
        if optargs[0].__dict__.get(key):
            SETTINGS[key] = optargs[0].__dict__[key]

    chdir(path.dirname(path.abspath(buildhck.__file__)))
    run(**buildhck.SETTINGS)

if __name__ == "__main__":
    main()
