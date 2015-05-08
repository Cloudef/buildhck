import json
import random

from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

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
