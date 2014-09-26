#!/usr/bin/env python3
# pylint: disable=line-too-long
'''buildhck python client'''

import os
import json
import shlex
from base64 import b64encode
from importlib import import_module

from protocols import DownloadException, NothingToDoException

import logging
logging.root.name = 'buildhck'

SETTINGS = {}
SETTINGS['builds_directory'] = 'builds'
SETTINGS['server'] = 'http://localhost:9001'
SETTINGS['auth'] = {}
SETTINGS['cleanup'] = False


class CookException(Exception):
    '''exception related to cooking, if this fails the failed data is sent'''


class RecipeException(Exception):
    '''exception raised when there was problem with recipe, if this fails nothing is sent'''


def s_mkdir(sdir):
    '''safe mkdir'''
    if not os.path.exists(sdir):
        os.mkdir(sdir)
    if not os.path.isdir(sdir):
        raise IOError("local path '{}' is not a directory".format(sdir))


def touch(path):
    '''touch file'''
    with open(path, 'a'):
        os.utime(path, None)


def expand_cmd(cmd, replace):
    '''expand commands from recipies'''
    cmd_list = shlex.split(cmd)
    for i, item in enumerate(cmd_list):
        for rep in replace:
            if rep in item:
                cmd_list[i] = item.replace(rep, replace[rep])
    logging.debug(cmd_list)
    return cmd_list


def run_cmd_catch_output(cmd):
    '''run command and catch output and return value'''
    from select import select
    from subprocess import Popen, PIPE
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)

    log = []
    while True:
        reads = [proc.stdout.fileno(), proc.stderr.fileno()]
        ret = select(reads, [], [])
        for fdi in ret[0]:
            if fdi == proc.stdout.fileno():
                log.append(proc.stdout.readline())
            elif fdi == proc.stderr.fileno():
                log.append(proc.stderr.readline())
        if proc.poll() is not None:
            break

    return {'code': proc.returncode, 'output': log}


def run_cmd_list_catch_output(cmd_list, result, expand):
    '''run commands in command list and catch output and return code'''
    log = []
    for cmd in cmd_list:
        expanded = expand_cmd(cmd, expand)
        ret = run_cmd_catch_output(expanded)
        if log:
            log.append(b'\n')
        log.append('>> {}:\n'.format(expanded).encode('UTF-8'))
        log.extend(ret['output'])
        if ret['code'] != os.EX_OK:
            result['status'] = 0
            result['log'] = b64encode(b''.join(log)).decode('UTF-8') if log else ''
            raise CookException('command failed: {}'.format(expanded))
    result['status'] = 1 if cmd_list else -1
    result['log'] = b64encode(b''.join(log)).decode('UTF-8') if log else ''


def prepare(recipe, srcdir, result):
    '''prepare project'''
    return run_cmd_list_catch_output(recipe.prepare, result, {'$srcdir': srcdir})


def build(recipe, srcdir, builddir, pkgdir, result):
    '''build project'''
    return run_cmd_list_catch_output(recipe.build, result, {'$srcdir': srcdir, '$builddir': builddir, '$pkgdir': pkgdir})


def test(recipe, srcdir, builddir, result):
    '''test project'''
    return run_cmd_list_catch_output(recipe.test, result, {'$srcdir': srcdir, '$builddir': builddir})


def package(recipe, srcdir, builddir, pkgdir, result):
    '''package project'''
    return run_cmd_list_catch_output(recipe.package, result, {'$srcdir': srcdir, '$builddir': builddir, '$pkgdir': pkgdir})


def download(recipe, srcdir, result):
    '''download recipe'''
    proto = ''
    fragment = ''
    branch = ''
    url = recipe.source

    split = recipe.source.split('+', 1)
    if split:
        proto = split[0]
        url = split[1]
        split = split[1].rsplit('#', 1)
    else:
        split = recipe.source.rsplit('#', 1)

    if len(split) > 1:
        url = split[0]
        fragment = split[1]

    if fragment:
        branch = fragment.partition("=")[2]
        if branch:
            result['branch'] = branch

    try:
        protocol = import_module('protocols.{}'.format(proto))
    except ImportError:
        raise RecipeException('Unknown protocol: {}'.format(proto))
    else:
        if not branch:
            result['branch'] = protocol.DEFAULT_BRANCH
        protocol.clone(srcdir, url, branch, result)


def perform_recipe(recipe, srcdir, builddir, pkgdir, result):
    '''perform recipe'''
    s_mkdir(srcdir)
    download(recipe, srcdir, result)

    if 'prepare' in recipe.__dict__:
        os.chdir(srcdir)
        prepare(recipe, srcdir, result['build'])

    s_mkdir(builddir)
    os.chdir(builddir)
    build(recipe, srcdir, builddir, pkgdir, result['build'])

    if 'test' in recipe.__dict__:
        test(recipe, srcdir, builddir, result['test'])
    else:
        result['test']['status'] = -1

    if 'package' in recipe.__dict__:
        s_mkdir(pkgdir)
        os.chdir(builddir)
        package(recipe, srcdir, builddir, pkgdir, result['package'])
    else:
        result['package']['status'] = -1


def cleanup_build(builddir, srcdir, pkgdir):
    '''cleanup build'''
    import shutil
    if builddir is not srcdir and os.path.exists(builddir) and os.path.isdir(builddir):
        shutil.rmtree(builddir)
    if os.path.exists(pkgdir) and os.path.isdir(pkgdir):
        shutil.rmtree(pkgdir)


def upload_build(recipe, result, srcdir):
    '''upload build'''
    try:
        service = import_module('services.{}'.format('buildhck'))
    except ImportError:
        raise Exception('TODO')

    for name in [recipe.name, '']:
        if name in SETTINGS['auth']:
            key = SETTINGS['auth'][name]
            break
    else:
        key = None

    if service.upload(recipe, result, SETTINGS['server'], key):
        touch(os.path.join(srcdir, '.buildhck_built'))
        logging.info('Build successfully sent to server.')
    # the error already got displayed


def cook_recipe(recipe):
    '''prepare && cook recipe'''

    logging.info('Building %s from %s', recipe.name, recipe.source)
    logging.debug(recipe.build)
    if 'test' in recipe.__dict__:
        logging.debug(recipe.test)
    if 'package' in recipe.__dict__:
        logging.debug(recipe.package)

    os.chdir(STARTDIR)
    s_mkdir(SETTINGS['builds_directory'])
    projectdir = os.path.abspath(os.path.join(SETTINGS['builds_directory'], recipe.name))

    pkgdir = os.path.abspath(os.path.join(projectdir, 'pkg'))
    srcdir = os.path.abspath(os.path.join(projectdir, 'src'))

    if 'build_in_srcdir' in recipe.__dict__ and recipe.build_in_srcdir:
        builddir = srcdir
    else:
        builddir = os.path.abspath(os.path.join(projectdir, 'build'))

    import socket
    result = {'client': socket.gethostname(),
              'build': {'status': -1},
              'test': {'status': -1},
              'package': {'status': -1}}

    if 'upstream' in recipe.__dict__ and recipe.upstream:
        result['upstream'] = recipe.upstream

    if 'github' in recipe.__dict__ and recipe.github:
        result['github'] = recipe.github

    s_mkdir(projectdir)
    send_build = True
    try:
        perform_recipe(recipe, srcdir, builddir, pkgdir, result)
    except CookException as exc:
        logging.error('{} build failed :: {}'.format(recipe.name, str(exc)))
    except RecipeException as exc:
        logging.error('{} recipe error :: {}'.format(recipe.name, str(exc)))
        send_build = False
    except DownloadException as exc:
        logging.error('{} download failed :: {}'.format(recipe.name, str(exc)))
        send_build = False
    except NothingToDoException:
        send_build = False

    if send_build:
        upload_build(recipe, result, srcdir)

    # cleanup build and pkg directory
    if SETTINGS['cleanup']:
        cleanup_build(srcdir, builddir, pkgdir)

    os.chdir(STARTDIR)


def main():
    '''main method'''
    from argparse import ArgumentParser
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('-s', '--server', dest='server',
                        help='buildhck server url')
    parser.add_argument('-b', '--buildsdir', dest='builds_directory',
                        help='directory for builds')
    parser.add_argument('-c', '--cleanup', action='store_true', dest='cleanup',
                        help='cleanup build and package directories after build')
    parser.add_argument('-a', '--auth', dest='auth', type=json.loads,
                        help='set authentication token for upload')
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                        help='print debug information')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='[%(name)s] [%(levelname)s]: %(message)s')

    try:
        import authorization
        if 'key' in authorization.__dict__:
            SETTINGS['auth'] = authorization.__dict__
        if 'server' in authorization.__dict__:
            SETTINGS['server'] = authorization.server
    except ImportError:
        logging.warn('Authorization module was not loaded!')

    for key in SETTINGS.keys():
        if args.__dict__.get(key):
            SETTINGS[key] = args.__dict__[key]

    for module in os.listdir('recipes'):
        if module.find("_recipe.py") == -1:
            continue
        modulebase = os.path.splitext(module)[0]
        cook_recipe(getattr(__import__("recipes", fromlist=[modulebase]), modulebase))

if __name__ == '__main__':
    STARTDIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(STARTDIR)
    main()
else:
    raise Exception('Should not be used as module')

#  vim: set ts=8 sw=4 tw=0 :
