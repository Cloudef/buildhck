#!/usr/bin/env python3

from os import chdir, path
from optparse import OptionParser

from bottle import run
from buildhck import buildhck, config

def main():
    '''main method'''
    parser = OptionParser()
    parser.add_option('-s', '--server', dest='server',
                      help='bottle.py WSGI server backend')
    parser.add_option('-p', '--port', dest='port',
                      help='server port')
    parser.add_option('-b', '--buildsdir', dest='builds_directory',
                      help='directory for builds')
    args = parser.parse_args()[0]

    config.config.update({k:v for k,v in vars(args).items() if v})

    chdir(path.dirname(path.abspath(buildhck.__file__)))
    run(**config.config)

if __name__ == "__main__":
    main()
