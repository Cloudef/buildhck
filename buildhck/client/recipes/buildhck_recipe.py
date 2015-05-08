# pylint: disable=C0103
'''buildhck recipe for buildhck'''

name = 'buildhck'
upstream = 'https://github.com/Cloudef/buildhck'
source = 'git+git://github.com/Cloudef/buildhck.git#branch=master'
build = ['python3 -m py_compile "$srcdir/buildhck.py"',
         'python3 -m py_compile "$srcdir/client/client.py"']
test = ['python3 "$srcdir/test.py"']
analyze = ['pylint "$srcdir/buildhck.py" "$srcdir/client/client.py"']
analyze_re = '^W:'

# vim: set ts=8 sw=3 tw=0
