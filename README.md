# Buildhck
[![buildhck status](http://cloudef.eu:9001/build/buildhck/master/linux%20x86_64/build-status.png)](#)

Micro build automation client/server framework

## Running tests

    ./test.py

## Installing

Since this is a WSGI application, there is no standard install prodecure.
You may run the buildhck.py standalone, or install wsgi application container such as uwsig to be used with web server such as nginx (recommended)

If running standalone, the default bottle.py WSGI backend is used which most likely will be slow.
You can use -s argument or server key on authorization.py to change this to something like cherrypy for example.
(See bottle.py documentation for more information)

If running standalone, it is good idea to isolate the process into its own user/group, maybe even write a systemd service or init script.

Whichever route you go, it is probably preferred you maintain fork of buildhck, so you can get upstream changes easily and do own modifications.

[uwsgi documentation](http://uwsgi-docs.readthedocs.org/en/latest/)
[bottlepy documentation (server options)](http://bottlepy.org/docs/dev/deployment.html#server-options)

## Usage

When you have builhck server up and running, opening the web page should show "No projects" text.
You can submit new build which buildhck creates project automatically if it does not exist.

The JSON for build is following:
```json
{
  "upstream": "upstream url",
  "client": "client name (computer)",
  "commit": "commit sha",
  "force": true/false,
  "description":"commit description",
  "build": { "status": -1/0/1, "log": "base64" },
  "test": { "status": -1/0/1, "log": "base64" },
  "package": { "status": -1/0/1, "log": "base64", "zip": "base64" },
  "analyze": { "status": number of warnings, "log": "base64" },
  "github": { "user": "github user", "repo": "github repository"}
}
```
```
status -1 == skipped
status  0 == failed
status  1 == OK
force replaces build if already submitted for the commit
logs and files should be base64 encoded
specify github for post-hook issues
```

The data should be submitted to `/build/<project name>/<branch name>/<system name>`

Buildhck is still under development so this format most likely will change.

Builds will be stored in 'builds' directory in current working directory.
The file structure is `project/branch/system/{current,timestamp}`
You may manually remove directories to remove builds or projects from buildhck.

Github integration needs api token server side. See the authorization.def.py.

For authentication and other options, refer to authorization.def.py.

## Client usage

You can use client.py provided by this repository, If you do not want to implement sending of builds yourself.
When client.py is ran it will read the recipes directory in current directory.

The example recipe looks like this:
```python
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
```
```
name = project name
upstream = upstream project source url
source = source code, currently only git (git+) and mercurial (hg+) is supported
build[] = commands to trigger for build
test[] = commands to trigger for test
package[] = commands to trigger for package
analyze[] = commands to trigger for analyze
analyze_re = regex used to find warnings from the analyze, by default line count of analyze output is used
```

You may automate builds by making the client.py run in intervals with cronjob or systemd timer.

For authorization and other options, refer to authorization.def.py.

## License

Not decided yet
