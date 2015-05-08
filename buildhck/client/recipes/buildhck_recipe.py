# pylint: disable=C0103
'''buildhck recipe for buildhck'''

name = 'buildhck'
upstream = 'https://github.com/Cloudef/buildhck'
source = 'git+git://github.com/Cloudef/buildhck.git#branch=master'
build = ['python3 -m py_compile "$srcdir/buildhck/buildhck.py"',
         'python3 -m py_compile "$srcdir/buildhck/client/client.py"']
test = ['tox']
analyze = ['pylint "$srcdir/buildhck/buildhck.py" "$srcdir/buildhck/client/client.py"']
package = ['python3 $srcdir/setup.py install --root="$pkgdir/"']
analyze_re = '^W:'

# tox needs tox.ini in $PWD
build_in_srcdir = True

# vim: set ts=8 sw=3 tw=0
