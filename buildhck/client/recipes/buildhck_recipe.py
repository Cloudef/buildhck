# pylint: disable=C0103
'''buildhck recipe for buildhck'''

name = 'buildhck'
upstream = 'https://github.com/Cloudef/buildhck'
source = 'git+git://github.com/Cloudef/buildhck.git#branch=master'
build = ['python3 "$srcdir/setup.py" build']
test = ['python3 "$srcdir/setup.py" test']
analyze = ['python3 "$srcdir/setup.py" lint']
package = ['python3 "$srcdir/setup.py" install --root="$pkgdir"']
analyze_re = '^W:'

# vim: set ts=8 sw=3 tw=0
