# pylint: disable=line-too-long
'''git module'''

import os
from subprocess import check_call, check_output
from . import DownloadException, NothingToDoException

def _git(*args):
    '''git wrapper'''
    return check_call(['git'] + list(args)) == os.EX_OK


def _git2(*args):
    '''git wrapper2'''
    return check_output(['git'] + list(args))


def clone(srcdir, url, branch, result):
    '''clone source using git'''
    if not branch:
        branch = DEFAULT_BRANCH

    oldcommit = ''
    if os.path.isdir(os.path.join(srcdir, '.git')):
        os.chdir(srcdir)
        oldcommit = _git2('rev-parse', 'HEAD').strip().decode('UTF-8')
        if not _git('--work-tree', srcdir, 'fetch', '-f', '-u', 'origin', '{}:{}'.format(branch, branch)):
            raise DownloadException('git fetch failed')
        if not _git('--work-tree', srcdir, 'checkout', '-f', branch):
            raise DownloadException('git checkout failed')
    elif not _git('clone', '--depth', '1', '-b', branch, url, srcdir):
        raise DownloadException('git clone failed')

    os.chdir(srcdir)
    result['commit'] = _git2('--work-tree', srcdir, 'rev-parse', 'HEAD').strip().decode('UTF-8')
    result['description'] = _git2('--work-tree', srcdir, 'log', '-1', '--pretty=%B').strip().decode('UTF-8')

    if os.path.exists(os.path.join(srcdir, '.buildhck_built')) and result['commit'] == oldcommit:
        raise NothingToDoException('There is nothing to build')


DEFAULT_BRANCH = 'master'
