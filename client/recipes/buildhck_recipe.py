# pylint: disable=C0103
"""buildhck recipe for buildhck"""

name = 'buildhck'
source = 'git+git://github.com/Cloudef/buildhck.git#branch=master'
prepare = []
build = ['python3 -m py_compile "$srcdir/buildhck.py"',
         'python3 -m py_compile "$srcdir/client.py"']
test = ['python3 "$srcdir/test.py"']
package = []

# disable github automation
github = {}

# vim: set ts=8 sw=3 tw=0
