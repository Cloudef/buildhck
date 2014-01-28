#!/usr/bin/env python3
# pylint: disable=C0301, R0904, R0201, W0212
"""unittests for buildhck"""

SERVER = 'http://localhost:9001'

import os, sys, time, json, unittest, subprocess
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from base64 import b64encode

def get_file(relative):
    """get file from server"""
    request = Request('{}/{}'.format(SERVER, quote(relative)))
    try:
        urlopen(request)
    except HTTPError:
        return False
    except URLError:
        return False
    return True

def send_build(data, project, branch, system):
    """send build to server and return response"""
    request = Request('{}/build/{}/{}/{}'.format(SERVER, quote(project), quote(branch), quote(system)))
    request.add_header('Content-Type', 'application/json')
    try:
        urlopen(request, json.dumps(data).encode('UTF-8'))
    except HTTPError:
        return False
    except URLError:
        return False
    return True

def delete_build(project, branch=None, system=None):
    """delete build from server"""
    request = None
    if not branch and not system:
        request = Request('{}/build/{}'.format(SERVER, quote(project)))
    elif branch and not system:
        request = Request('{}/build/{}/{}'.format(SERVER, quote(project), quote(branch)))
    else:
        request = Request('{}/build/{}/{}/{}'.format(SERVER, quote(project), quote(branch), quote(system)))
    request.get_method = lambda: 'DELETE'
    try:
        urlopen(request)
    except HTTPError:
        return False
    except URLError:
        return False
    return True

def get_build_file(project, branch, system, bfile):
    """get file for build"""
    request = Request('{}/build/{}/{}/{}/{}'.format(SERVER, quote(project), quote(branch), quote(system), quote(bfile)))
    try:
        urlopen(request)
    except HTTPError:
        return False
    except URLError:
        return False
    return True

class TestIndexFunctions(unittest.TestCase):
    """index test routine"""

    def test_index(self):
        """index page"""
        assert get_file('') == True

    def test_favicon(self):
        """favicon"""
        assert get_file('favicon.ico') == True

    def test_platform_icons(self):
        """platform icons"""
        assert get_file('platform/unknown.png') == True
        assert get_file('platform/linux.png') == True
        assert get_file('platform/darwin.png') == True
        assert get_file('platform/windows.png') == True
        assert get_file('platform/bsd.png') == True

class TestBuildFunctions(unittest.TestCase):
    """build test routine"""

    def test_send(self):
        """test build data send"""
        assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', 'unittest') == True
        assert send_build({'client': 'unittest', 'build': {'status': 'notint'}, 'test': 0}, 'unittest', 'unittest', 'unittest') == False
        assert send_build({'client': 'unittest', 'build': {'status': 2}, 'test': {'status': 2}}, 'unittest', 'unittest', 'unittest') == False
        assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, '/;:#%-\\', 'unittest', 'unittest') == False
        assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', '/;:#%-\\', 'unittest') == False
        assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', '/;:#%-\\') == False

    def test_delete(self):
        """test build deletion"""
        assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', 'unittest') == True
        assert delete_build('unittest') == True

        assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', 'unittest') == True
        assert delete_build('unittest', 'unittest') == True

        assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', 'unittest') == True
        assert delete_build('unittest', 'unittest', 'unittest') == True

        assert delete_build('unittest', 'unittest', 'unittest') == False
        assert delete_build('unittest', 'unittest') == False
        assert delete_build('unittest') == False

    def test_build_files(self):
        """test build related file access"""
        assert get_build_file('unittest', 'unittest', 'unittest', 'build-log.txt') == False
        assert get_build_file('unittest', 'unittest', 'unittest', 'build-log.bz2') == False
        assert get_build_file('unittest', 'unittest', 'unittest', 'test-log.txt') == False
        assert get_build_file('unittest', 'unittest', 'unittest', 'test-log.bz2') == False
        assert get_build_file('unittest', 'unittest', 'unittest', 'package-log.txt') == False
        assert get_build_file('unittest', 'unittest', 'unittest', 'package-log.bz2') == False
        assert get_build_file('unittest', 'unittest', 'unittest', 'package.zip') == False
        assert get_build_file('unittest', 'unittest', 'unittest', 'build-status.png') == False

        assert send_build({'client': 'unittest', 'build': {'status': 1, 'log': b64encode(b'hello world').decode('UTF-8')}, 'test': {'status': 1, 'log': b64encode(b'hello world').decode('UTF-8')}}, 'unittest', 'unittest', 'unittest') == True

        assert get_build_file('unittest', 'unittest', 'unittest', 'build-log.txt') == True
        assert get_build_file('unittest', 'unittest', 'unittest', 'build-log.bz2') == True
        assert get_build_file('unittest', 'unittest', 'unittest', 'test-log.txt') == True
        assert get_build_file('unittest', 'unittest', 'unittest', 'test-log.bz2') == True
        assert get_build_file('unittest', 'unittest', 'unittest', 'build-status.png') == True

    def tearDown(self):
        """cleanup test"""
        delete_build('unittest') # don't care about return

if __name__ == '__main__':
    PID = os.fork()
    if PID:
        time.sleep(1)
        RET = unittest.main(exit=False)
        os.kill(PID, 2)
        sys.exit(os.EX_OK if RET.result.wasSuccessful() else 1)
    else:
        try:
            FLE = open(os.devnull, 'w')
            subprocess.call(['python3', 'buildhck.py'], stdout=FLE, stderr=FLE)
        except KeyboardInterrupt:
            pass
        finally:
            FLE.close()
        os._exit(os.EX_OK)

#  vim: set ts=8 sw=4 tw=0 :
