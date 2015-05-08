# pylint: disable=line-too-long
'''hg module'''

import os
from subprocess import check_call, check_output
from . import DownloadException, NothingToDoException

def _hg(*args):
    '''hg wrapper'''
    return check_call(['hg'] + list(args)) == os.EX_OK


def _hg2(*args):
    '''hg wrapper2'''
    return check_output(['hg'] + list(args))


def clone(srcdir, url, branch, result):
    '''clone source using hg'''
    if not branch:
        branch = DEFAULT_BRANCH

    oldcommit = ''
    if os.path.isdir(os.path.join(srcdir, '.hg')):
        os.chdir(srcdir)
        oldcommit = _hg2('tip', '--quiet').strip().decode('UTF-8')
        if not _hg('pull'):
            raise DownloadException('hg pull failed')
        if not _hg('update', '-C', branch):
            raise DownloadException('hg update failed')
    elif not _hg('clone', '-b', branch, url, srcdir):
        raise DownloadException('hg clone failed')

    os.chdir(srcdir)
    result['commit'] = _hg2('tip', '--quiet').strip().decode('UTF-8')
    result['description'] = _hg2('log', '-l1', '--template', '{desc}').decode('UTF-8')

    if os.path.exists(os.path.join(srcdir, '.buildhck_built')) and result['commit'] == oldcommit:
        raise NothingToDoException('There is nothing to build')


DEFAULT_BRANCH = 'default'
