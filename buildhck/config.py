import yaml
from xdg import BaseDirectory

config = \
{
    'build_directory': 'builds',
    'github': {},
    'auth': {},
    'server': 'auto',
    'port': 9001
}

def load():
    for path in BaseDirectory.load_config_paths('buildhck', 'config.yaml'):
        with open(path) as f:
            obj = yaml.load(f)
            config.update(obj)

load()
