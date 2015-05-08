from os import path, chdir
from time import sleep
from random import randint
from multiprocessing import Process

from pytest import fixture

from buildhck import buildhck, config
from bottle import run

import util
from util import get_file

def stupid(port):
    chdir(path.dirname(path.abspath(buildhck.__file__)))
    run(port=port)

@fixture(scope="session", autouse=True)
def buildhck_server(request):
    STARTDIR = path.dirname(path.abspath(__file__))
    chdir(STARTDIR)

    # FIXME: terrible hacks
    port = randint(49152, 65535)
    util.SERVER = 'http://localhost:{}'.format(port)
    p = Process(target=stupid, args=(port,))
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
