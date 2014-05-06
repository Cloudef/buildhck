#!/usr/bin/env python3
# pylint: disable=line-too-long
'''buildhck python client'''

import os, json, shlex
from base64 import b64encode

SETTINGS = {}
SETTINGS['builds_directory'] = 'builds'
SETTINGS['server'] = 'http://localhost:9001'
SETTINGS['auth'] = {}
SETTINGS['cleanup'] = False

class CookException(Exception):
    '''exception related to cooking, if this fails the failed data is sent'''
class RecipeException(Exception):
    '''exception raised when there was problem with recipe, if this fails nothing is sent'''
class DownloadException(Exception):
    '''expection raised when there was problem with download, if this fails nothing is sent'''
class NothingToDoException(Exception):
    '''expection raised when there is nothing to cook, if this fails nothing is sent'''

try:
    import authorization
    if 'key' in authorization.__dict__:
        SETTINGS['auth'] = authorization.__dict__
    if 'server' in authorization.__dict__:
        SETTINGS['server'] = authorization.server
except ImportError as exc:
    print("Authorization module was not loaded!")

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
    print(cmd_list)
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
        if proc.poll() != None:
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

def clone_git(srcdir, url, branch, result):
    '''clone source using git'''
    def git(*args):
        '''git wrapper'''
        from subprocess import check_call
        return check_call(['git'] + list(args)) == os.EX_OK

    def git2(*args):
        '''git wrapper2'''
        from subprocess import check_output
        return check_output(['git'] + list(args))

    if not branch:
        branch = 'master'

    oldcommit = ''
    if os.path.isdir(os.path.join(srcdir, '.git')):
        os.chdir(srcdir)
        oldcommit = git2('rev-parse', 'HEAD').strip().decode('UTF-8')
        if not git('fetch', '-f', '-u', 'origin', '{}:{}'.format(branch, branch)):
            raise DownloadException('git fetch failed')
        if not git('checkout', '-f', '{}'.format(branch)):
            raise DownloadException('git checkout failed')
    elif not git('clone', '--depth', '1', '-b', branch, url, srcdir):
        raise DownloadException('git clone failed')

    os.chdir(srcdir)
    result['commit'] = git2('rev-parse', 'HEAD').strip().decode('UTF-8')
    result['description'] = git2('log', '-1', '--pretty=%B').strip().decode('UTF-8')

    if os.path.exists(os.path.join(srcdir, '.buildhck_built')) and result['commit'] == oldcommit:
        raise NothingToDoException('There is nothing to build')

def clone_hg(srcdir, url, branch, result):
    '''clone source using hg'''
    def hg(*args):
        '''hg wrapper'''
        # pylint: disable=invalid-name
        from subprocess import check_call
        return check_call(['hg'] + list(args)) == os.EX_OK

    def hg2(*args):
        '''hg wrapper2'''
        from subprocess import check_output
        return check_output(['hg'] + list(args))

    if not branch:
        branch = 'default'

    oldcommit = ''
    if os.path.isdir(os.path.join(srcdir, '.hg')):
        os.chdir(srcdir)
        oldcommit = hg2('tip', '--quiet').strip().decode('UTF-8')
        if not hg('pull'):
            raise DownloadException('hg pull failed')
        if not hg('update', branch):
            raise DownloadException('hg update failed')
    elif not hg('clone', '-b', branch, url, srcdir):
        raise DownloadException('hg clone failed')

    os.chdir(srcdir)
    result['commit'] = hg2('tip', '--quiet').strip().decode('UTF-8')
    result['description'] = hg2('log', '-l1', '--template', '{desc}').decode('UTF-8')

    if os.path.exists(os.path.join(srcdir, '.buildhck_built')) and result['commit'] == oldcommit:
        raise NothingToDoException('There is nothing to build')

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

    if proto == 'git':
        if not branch:
            result['branch'] = 'master'
        clone_git(srcdir, url, branch, result)
        return
    if proto == 'hg':
        if not branch:
            result['branch'] = 'default'
        clone_hg(srcdir, url, branch, result)
        return

    raise RecipeException('Unknown protocol: {}'.format(proto))

def perform_recipe(recipe, srcdir, builddir, pkgdir, result):
    '''perform recipe'''
    s_mkdir(srcdir)
    download(recipe, srcdir, result)

    if 'prepare' in recipe.__dict__:
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

def cook_recipe(recipe):
    '''prepare && cook recipe'''
    # pylint: disable=too-many-branches, too-many-statements, too-many-locals

    print('')
    print(recipe.name)
    print(recipe.source)
    print(recipe.build)
    if 'test' in recipe.__dict__:
        print(recipe.test)
    if 'package' in recipe.__dict__:
        print(recipe.package)
    print('')

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

    if 'github' in recipe.__dict__ and recipe.github:
        result['github'] = recipe.github

    s_mkdir(projectdir)
    send_build = True
    try:
        perform_recipe(recipe, srcdir, builddir, pkgdir, result)
    except CookException as exc:
        print('{} build failed :: {}'.format(recipe.name, str(exc)))
    except RecipeException as exc:
        print('{} recipe error :: {}'.format(recipe.name, str(exc)))
        send_build = False
    except DownloadException as exc:
        print('{} download failed :: {}'.format(recipe.name, str(exc)))
        send_build = False
    except NothingToDoException:
        send_build = False

    if send_build:
        branch = result.pop('branch', 'unknown')

        key = ''
        if recipe.name in SETTINGS['auth']:
            key = SETTINGS['auth'][recipe.name]
        elif '' in SETTINGS['auth']:
            key = SETTINGS['auth']['']

        import sys, platform
        from urllib.parse import quote
        from urllib.request import Request, urlopen
        from urllib.error import URLError, HTTPError
        request = Request('{}/build/{}/{}/{}'.format(SETTINGS['server'],
            quote(recipe.name), quote(branch), quote('{} {}'.format(sys.platform, platform.machine()))))

        request.add_header('Content-Type', 'application/json')
        if key:
            request.add_header('Authorization', key)

        try:
            urlopen(request, json.dumps(result).encode('UTF-8'))
        except HTTPError as exc:
            print("The server couldn't fulfill the request.")
            print('Error code: ', exc.code)
            if exc.code == 400:
                print("Client is broken, wrong syntax given to server")
            elif exc.code == 401:
                print("Wrong key provided for project.")
        except URLError as exc:
            print('Failed to reach a server.')
            print('Reason: ', exc.reason)
        else:
            touch(os.path.join(srcdir, '.buildhck_built'))
            print('Build successfully sent to server.')

    # cleanup build and pkg directory
    if SETTINGS['cleanup']:
        import shutil
        if builddir is not srcdir and os.path.exists(builddir) and os.path.isdir(builddir):
            shutil.rmtree(builddir)
        if os.path.exists(pkgdir) and os.path.isdir(pkgdir):
            shutil.rmtree(pkgdir)

    os.chdir(STARTDIR)

def main():
    '''main method'''
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-s', '--server', dest='server',
                      help='buildhck server url')
    parser.add_option('-b', '--buildsdir', dest='builds_directory',
                      help='directory for builds')
    parser.add_option('-c', '--cleanup', dest='cleanup',
                      help='cleanup build and package directories after build')
    optargs = parser.parse_args()

    for key in SETTINGS.keys():
        if optargs[0].__dict__.get(key):
            SETTINGS[key] = optargs[0].__dict__[key]

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
