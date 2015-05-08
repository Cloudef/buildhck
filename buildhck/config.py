import yaml
from os import path, makedirs
from xdg import BaseDirectory

config = \
{
    'github': {},
    'auth': {},
    'serverurl': 'http://localhost:9001',
    'port': 9001
}

def load():
    for config_path in BaseDirectory.load_config_paths('buildhck', 'config.yaml'):
        with open(config_path) as f:
            obj = yaml.load(f)
            if obj:
                config.update(obj)
    if not path.isdir(build_directory()):
        makedirs(build_directory())

def build_directory(*args):
    data_path = BaseDirectory.save_data_path('buildhck')
    p = path.join(data_path, config.get('builds_directory', 'builds'), *args)
    return p

load()
