# pylint: disable=C0301, R0904, R0201, W0212
"""unittests for buildhck"""

import os, sys, time, json, unittest, subprocess, signal, shutil
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from base64 import b64encode
import random

# FIXME: need to check return status
def get_file(relative):
    """get file from server"""
    request = Request('{}/{}'.format(SERVER, quote(relative)))
    try:
        return urlopen(request)
    except (HTTPError, URLError):
        pass

def send_build(data, project, branch, system):
    """send build to server and return response"""
    request = Request('{}/build/{}/{}/{}'.format(SERVER, quote(project), quote(branch), quote(system)))
    request.add_header('Content-Type', 'application/json')
    try:
        return urlopen(request, json.dumps(data).encode('UTF-8'))
    except (HTTPError, URLError):
        pass

def delete_build(project, branch=None, system=None, fsdate=None):
    """delete build from server"""
    request = None
    if not branch and not system:
        request = Request('{}/build/{}'.format(SERVER, quote(project)))
    elif branch and not system:
        request = Request('{}/build/{}/{}'.format(SERVER, quote(project), quote(branch)))
    elif branch and system and not fsdate:
        request = Request('{}/build/{}/{}/{}'.format(SERVER, quote(project), quote(branch), quote(system)))
    else:
        request = Request('{}/build/{}/{}/{}/{}'.format(SERVER, quote(project), quote(branch), quote(system), quote(fsdate)))
    request.get_method = lambda: 'DELETE'
    try:
        return urlopen(request)
    except (HTTPError, URLError):
        pass

def get_build_file(project, branch, system, bfile):
    """get file for build"""
    request = Request('{}/build/{}/{}/{}/current/{}'.format(SERVER, quote(project), quote(branch), quote(system), quote(bfile)))
    try:
        return urlopen(request)
    except (HTTPError, URLError):
        pass

class TestIndexFunctions(unittest.TestCase):
    """index test routine"""

    def test_index(self):
        """index page"""
        assert get_file('')

    def test_favicon(self):
        """favicon"""
        assert get_file('favicon.ico')

    def test_platform_icons(self):
        """platform icons"""
        assert get_file('platform/unknown.png')
        assert get_file('platform/linux.png')
        assert get_file('platform/darwin.png')
        assert get_file('platform/windows.png')
        assert get_file('platform/bsd.png')

class TestBuildFunctions(unittest.TestCase):
    """build test routine"""

    def test_send(self):
        """test build data send"""
        assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', 'unittest')
        assert send_build({'force': True, 'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', 'unittest')
        assert not send_build({'client': 'unittest', 'build': {'status': 'notint'}, 'test': 0}, 'unittest', 'unittest', 'unittest')
        assert not send_build({'client': 'unittest', 'build': {'status': 2}, 'test': {'status': 2}}, 'unittest', 'unittest', 'unittest')
        assert not send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, '/;:#%-\\', 'unittest', 'unittest')
        assert not send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', '/;:#%-\\', 'unittest')
        assert not send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', '/;:#%-\\')

    def test_delete(self):
        """test build deletion"""
        assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', 'unittest')
        assert delete_build('unittest')

        assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', 'unittest')
        assert delete_build('unittest', 'unittest')

        assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', 'unittest')
        assert delete_build('unittest', 'unittest', 'unittest')

        assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', 'unittest')
        assert delete_build('unittest', 'unittest', 'unittest', 'current')

        assert not delete_build('unittest', 'unittest', 'unittest', 'current')
        assert not delete_build('unittest', 'unittest', 'unittest')
        assert not delete_build('unittest', 'unittest')
        assert not delete_build('unittest')

    def test_build_files(self):
        """test build related file access"""
        assert not get_build_file('unittest', 'unittest', 'unittest', 'build-log.txt')
        assert not get_build_file('unittest', 'unittest', 'unittest', 'build-log.bz2')
        assert not get_build_file('unittest', 'unittest', 'unittest', 'test-log.txt')
        assert not get_build_file('unittest', 'unittest', 'unittest', 'test-log.bz2')
        assert not get_build_file('unittest', 'unittest', 'unittest', 'package-log.txt')
        assert not get_build_file('unittest', 'unittest', 'unittest', 'package-log.bz2')
        assert not get_build_file('unittest', 'unittest', 'unittest', 'package.zip')
        assert not get_build_file('unittest', 'unittest', 'unittest', 'build-status.png')

        assert send_build({'client': 'unittest', 'build': {'status': 1, 'log': b64encode(b'hello world').decode('UTF-8')}, 'test': {'status': 1, 'log': b64encode(b'hello world').decode('UTF-8')}}, 'unittest', 'unittest', 'unittest')

        assert get_build_file('unittest', 'unittest', 'unittest', 'build-log.txt')
        assert get_build_file('unittest', 'unittest', 'unittest', 'build-log.bz2')
        assert get_build_file('unittest', 'unittest', 'unittest', 'test-log.txt')
        assert get_build_file('unittest', 'unittest', 'unittest', 'test-log.bz2')
        assert get_build_file('unittest', 'unittest', 'unittest', 'build-status.png')

    def teardown_method(self, method):
        """cleanup test"""
        delete_build('unittest') # don't care about return

def setup_module(module):
    STARTDIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(STARTDIR)

    # FIXME: terrible hack
    port = random.randint(49152, 65535)
    module.SERVER = 'http://localhost:{}'.format(port)
    module.__testdir = '/tmp/buildhck_{}'.format(port)
    module.__p = subprocess.Popen(['python3', '-m', 'buildhck.buildhck', '-b', module.__testdir, '-p', str(port)])
    for _ in range(30):
        if module.__p.poll():
            raise ChildProcessError('buildhck terminated prematurely')
        if get_file(''):
            break
        time.sleep(1)
    else:
        raise TimeoutError('failed to start buildhck')

def teardown_module(module):
    module.__p.send_signal(signal.SIGINT)
    module.__p.communicate()
    shutil.rmtree(module.__testdir)

#  vim: set ts=8 sw=4 tw=0 :
