from os import path, chdir
from time import sleep
from random import randint
from multiprocessing import Process

from pytest import fixture

from buildhck import buildhck, config
from bottle import run

import util
from util import get_file

@fixture(scope="session", autouse=True)
def buildhck_server(request):
    # FIXME: terrible hacks
    port = randint(49152, 65535)
    util.SERVER = 'http://localhost:{}'.format(port)
    p = Process(target=run, kwargs={'port': port})
    p.start()
    for _ in range(30):
        if p.is_alive() and get_file(''):
           break
        sleep(0.25)
    else:
        raise TimeoutError('failed to start buildhck')

    def fin():
        p.terminate()
        p.join()
    request.addfinalizer(fin)

    return p
