'''buildhck module'''

import json
import logging
import sys
import platform
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def upload(recipe, result, server, key=None):
    '''upload build'''
    branch = result.pop('branch', 'unknown')

    request = Request('{}/build/{}/{}/{}'.format(
        server, quote(recipe.name), quote(branch),
        quote('{} {}'.format(sys.platform, platform.machine()))))

    request.add_header('Content-Type', 'application/json')
    if key is not None:
        request.add_header('Authorization', key)

    try:
        urlopen(request, json.dumps(result).encode('UTF-8'))
    except HTTPError as exc:
        logging.error("The server couldn't fulfill the request.")
        logging.error('Error code: %s', exc.code)
        if exc.code == 400:
            logging.error("Client is broken, wrong syntax given to server")
        elif exc.code == 401:
            logging.error("Wrong key provided for project.")
        logging.error("%s", exc.read())
        return False
    except URLError as exc:
        logging.error('Failed to reach a server.')
        logging.error('Reason: %s', exc.reason)
        return False

    return True
