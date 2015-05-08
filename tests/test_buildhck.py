# pylint: disable=C0301, R0904, R0201, W0212

from util import send_build, delete_build, get_build_file
from base64 import b64encode

def test_send():
    """test build data send"""
    assert send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', 'unittest')
    assert send_build({'force': True, 'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', 'unittest')
    assert not send_build({'client': 'unittest', 'build': {'status': 'notint'}, 'test': 0}, 'unittest', 'unittest', 'unittest')
    assert not send_build({'client': 'unittest', 'build': {'status': 2}, 'test': {'status': 2}}, 'unittest', 'unittest', 'unittest')
    assert not send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, '/;:#%-\\', 'unittest', 'unittest')
    assert not send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', '/;:#%-\\', 'unittest')
    assert not send_build({'client': 'unittest', 'build': {'status': 1}, 'test': {'status': 1}}, 'unittest', 'unittest', '/;:#%-\\')

def test_delete():
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

def test_build_files():
    """test build related file access"""
    assert not get_build_file('unittest', 'unittest', 'unittest', 'build-log.txt')
    assert not get_build_file('unittest', 'unittest', 'unittest', 'build-log.bz2')
    assert not get_build_file('unittest', 'unittest', 'unittest', 'test-log.txt')
    assert not get_build_file('unittest', 'unittest', 'unittest', 'test-log.bz2')
    assert not get_build_file('unittest', 'unittest', 'unittest', 'package-log.txt')
    assert not get_build_file('unittest', 'unittest', 'unittest', 'package-log.bz2')
    assert not get_build_file('unittest', 'unittest', 'unittest', 'package.zip')
    assert not get_build_file('unittest', 'unittest', 'unittest', 'build-status.svg')

    assert send_build({'client': 'unittest', 'build': {'status': 1, 'log': b64encode(b'hello world').decode('UTF-8')}, 'test': {'status': 1, 'log': b64encode(b'hello world').decode('UTF-8')}}, 'unittest', 'unittest', 'unittest')

    assert get_build_file('unittest', 'unittest', 'unittest', 'build-log.txt')
    assert get_build_file('unittest', 'unittest', 'unittest', 'build-log.bz2')
    assert get_build_file('unittest', 'unittest', 'unittest', 'test-log.txt')
    assert get_build_file('unittest', 'unittest', 'unittest', 'test-log.bz2')
    assert get_build_file('unittest', 'unittest', 'unittest', 'status.svg')

def teardown_method(self, method):
    """cleanup test"""
    delete_build('unittest') # don't care about return

#  vim: set ts=8 sw=4 tw=0 :
