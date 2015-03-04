#!/usr/bin/env python3
# pylint: disable=line-too-long
'''automatic build system client/server framework'''

import lib.bottle as bottle
from lib.bottle import BaseTemplate, template
from lib.bottle import static_file, response, request, redirect, route, abort, run
from lib.header import supported_request
from base64 import b64decode
from datetime import datetime
from urllib.parse import quote
import os, re, bz2, json

bottle.BaseRequest.MEMFILE_MAX = 4096 * 1024

SETTINGS = {}
SETTINGS['builds_directory'] = 'builds'
SETTINGS['github'] = {}
SETTINGS['auth'] = {}
SETTINGS['server'] = 'auto'
SETTINGS['port'] = 9001

ACCEPT = ['text/html', 'application/json']

STUSKEYS = ['build', 'test', 'package', 'analyze']

BUILDJSONMDL = {'upstream': '',
                'client': 'unknown client',
                'commit': 'unknown commit', 'description': '',
                'force': False,
                'build': {'status': -1, 'log': ''},
                'test': {'status': -1, 'log': ''},
                'package': {'status': -1, 'log': '', 'zip': ''},
                'analyze': {'status': -1, 'log': ''},
                'github': {'user': '', 'repo': ''}}

FNFILTERPROG = re.compile(r'[:;*?"<>|()\\]')

SCODEMAP = {-1: 'SKIP', 0: 'FAIL', 1: 'OK'}

try:
    # pylint: disable=import-error
    import authorization
    if 'auth' in authorization.__dict__:
        SETTINGS['auth'] = authorization.key
    if 'github' in authorization.__dict__:
        SETTINGS['github'] = authorization.github
    if 'server' in authorization.__dict__:
        SETTINGS['server'] = authorization.server
    if 'port' in authorization.__dict__:
        SETTINGS['port'] = authorization.port
except ImportError as exc:
    print("Authorization module was not loaded!")

def is_json_request():
    '''check if the request is json'''
    if 'Accept' in request.headers and supported_request(request.headers['Accept'], ACCEPT) == 'application/json':
        return True
    return False

def dump_json(dic):
    '''dump json data'''
    request.content_type = 'application/json'
    return json.dumps(dic)

def remove_control_characters(txt):
    '''remove control characters from string'''
    import unicodedata
    result = []
    lines = txt.splitlines()
    for line in lines:
        result.append(''.join(char for char in line if unicodedata.category(char)[0] != 'C'))
    return '\n'.join(result)

def validate_build(project, branch=None, system=None):
    '''validate build information'''
    if FNFILTERPROG.search(project):
        abort(400, 'project name contains invalid characters (invalid: :;*?"<>|()\\)')
    if branch and FNFILTERPROG.search(branch):
        abort(400, 'branch name contains invalid characters (invalid: :;*?"<>|()\\)')
    if system and FNFILTERPROG.search(system):
        abort(400, 'system name contains invalid characters (invalid: :;*?"<>|()\\)')

def is_authenticated_for_project(project):
    '''is client authenticated to send build information'''
    validate_build(project)

    # allow if our dict is empty
    if not SETTINGS['auth']:
        return True

    key = ''
    auth = SETTINGS['auth']
    if 'Authorization' in request.headers:
        key = request.headers['Authorization']

    # allow if key matches the one in dict
    # or the key in dict is empty for the project
    if project in auth and (auth[project] == key or not auth[project]):
        return True

    # allow if key matches public key, and
    # project is not specified explictly in dict
    if project not in auth and '' in auth and auth[''] == key:
        return True

    return False

def s_mkdir(sdir):
    '''safe mkdir'''
    if not os.path.exists(sdir):
        os.mkdir(sdir)
    if not os.path.isdir(sdir):
        raise IOError("local path '{}' is not a directory".format(sdir))

def github_issue(user, repo, subject, body, issueid=None, close=False):
    '''create/comment/delete github issue'''
    # pylint: disable=too-many-arguments

    if not SETTINGS['github']:
        print("no github_token specified, won't handle issue request")
        return None

    if close and not issueid:
        print("can't close github issue without id")
        return None

    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError

    data = None
    handle = None
    apiroot = 'https://api.github.com'

    if not issueid and not close: # create issue
        data = {'title': subject, 'body': body}
        handle = Request('{}/repos/{}/{}/issues'.format(apiroot, quote(user), quote(repo)))
    elif issueid and not close: # comment
        data = {'body': body}
        handle = Request('{}/repos/{}/{}/issues/{}/comments'.format(apiroot, quote(user), quote(repo), issueid))
    elif issueid and close: # close
        data = {'state': 'close'}
        handle = Request('{}/repos/{}/{}/issues/{}'.format(apiroot, quote(user), quote(repo), issueid))
        handle.get_method = lambda: 'PATCH'

    handle.add_header('Content-Type', 'application/json')
    handle.add_header('Accept', 'application/vnd.github.v3+json')
    handle.add_header('Authorization', 'token {}'.format(SETTINGS['github']))

    srvdata = None
    try:
        srvdata = urlopen(handle, json.dumps(data).encode('UTF-8'))
    except HTTPError as exc:
        print("The server couldn't fulfill the request.")
        print('Error code: ', exc.code)
        print(exc.read())
        return None
    except URLError as exc:
        print('Failed to reach a server.')
        print('Reason: ', exc.reason)
        return None

    if not srvdata:
        return None

    if not issueid:
        issueid = json.loads(srvdata.readall().decode('UTF-8'))['number']
        print("[GITHUB] issue created ({})".format(issueid))
    else:
        print("[GITHUB] issue updated ({})".format(issueid))

    return issueid if not close else None

def handle_github(project, branch, system, fsdate, metadata):
    '''handle github posthook for build'''
    github = metadata['github']

    if 'issueid' not in github:
        github['issueid'] = None

    failed = failure_for_metadata(metadata)

    if not github or (not failed and not github['issueid']):
        return # nothing to do

    build = get_build_data(project, branch, system, fsdate, get_history=False, in_metadata=metadata)
    for idx in range(len(build['url'])):
        build['url'][idx] = absolute_link(build['url'][idx][1:])
    build['systemimage'] = absolute_link(build['systemimage'][1:])

    subject = template('github_issue', build=build, subject=True)
    body = template('github_issue', build=build, subject=False)
    github['issueid'] = github_issue(github['user'], github['repo'], subject, body, github['issueid'], not failed)

def check_github_posthook(data, metadata):
    '''check if github posthook should be used'''
    if not data['github'] or not data['github']['user'] or not data['github']['repo']:
        return False

    issueid = None
    if 'github' in metadata and metadata['github'] and 'issueid' in metadata['github']:
        issueid = metadata['github']['issueid']

    metadata['github'] = {'user': data['github']['user'],
                          'repo': data['github']['repo'],
                          'issueid': issueid}
    return True

def build_exists(project, branch=None, system=None, fsdate=None):
    '''check if build dir exists'''
    validate_build(project, branch, system)
    buildpath = os.path.join(SETTINGS['builds_directory'], project)
    if branch:
        buildpath = os.path.join(buildpath, branch)
    if system:
        buildpath = os.path.join(buildpath, system)
    if fsdate:
        buildpath = os.path.join(buildpath, fsdate)
    return os.path.exists(buildpath)

def delete_build(project, branch=None, system=None, fsdate=None):
    '''delete build'''
    # pylint: disable=too-many-branches

    validate_build(project, branch, system)

    parentpath = None
    buildpath = os.path.join(SETTINGS['builds_directory'], project)
    if branch:
        parentpath = buildpath
        buildpath = os.path.join(buildpath, branch)
    if system:
        parentpath = buildpath
        buildpath = os.path.join(buildpath, system)
    if fsdate:
        parentpath = buildpath
        currentpath = os.path.join(buildpath, 'current')
        if fsdate == 'current':
            if os.path.lexists(currentpath):
                fsdate = os.readlink(currentpath)
            else:
                abort(404, 'Current build does not exist')
        buildpath = os.path.join(buildpath, fsdate)
    if not os.path.isdir(buildpath):
        return False

    import shutil
    shutil.rmtree(buildpath)

    if fsdate and os.path.lexists(currentpath):
        current = os.readlink(currentpath)
        if current == fsdate:
            latest = os.path.basename(sorted(os.listdir(parentpath))[0])
            if os.path.lexists(currentpath):
                os.unlink(currentpath)
            if latest != 'current':
                os.symlink(latest, currentpath)

    if fsdate and not os.listdir(parentpath):
        delete_build(project, branch, system)
    if system and not fsdate and not os.listdir(parentpath):
        delete_build(project, branch)
    if branch and not system and not os.listdir(parentpath):
        delete_build(project)
    return True

def save_build(project, branch, system, data):
    '''save build to disk'''
    # pylint: disable=too-many-locals
    validate_build(project, branch, system)
    if not data:
        raise ValueError('build should have data')

    metadata = metadata_for_build(project, branch, system, 'current')
    if 'commit' in metadata and metadata['commit'] == data['commit']:
        if not data['force']:
            print('This commit is already built')
            return
        delete_build(project, branch, system, 'current')

    date = datetime.utcnow()
    fsdate = date.strftime("%Y%m%d%H%M%S")
    s_mkdir(SETTINGS['builds_directory'])
    buildpath = os.path.join(SETTINGS['builds_directory'], project)
    s_mkdir(buildpath)
    buildpath = os.path.join(buildpath, branch)
    s_mkdir(buildpath)
    buildpath = os.path.join(buildpath, system)
    s_mkdir(buildpath)
    currentpath = os.path.join(buildpath, 'current')
    buildpath = os.path.join(buildpath, fsdate)
    s_mkdir(buildpath)

    metadata['date'] = date.isoformat()
    metadata['client'] = data['client']
    metadata['commit'] = data['commit']
    metadata['description'] = data['description']
    metadata['upstream'] = data['upstream']

    posthook = {}
    posthook['github'] = check_github_posthook(data, metadata)

    for key, value in data.items():
        if key not in STUSKEYS:
            continue

        metadata[key] = {'status': value['status']}

        if 'log' in value and value['log']:
            text = remove_control_characters(b64decode(value['log'].encode('UTF-8')).decode('UTF-8'))
            buildlog = bz2.compress(text.encode('UTF-8'))
            with open(os.path.join(buildpath, '{}-log.bz2'.format(key)), 'wb') as fle:
                fle.write(buildlog)

        if 'zip' in value and value['zip']:
            buildzip = b64decode(value['zip'].encode('UTF-8'))
            with open(os.path.join(buildpath, '{}.zip'.format(key)), 'wb') as fle:
                fle.write(buildzip)

    with open(os.path.join(buildpath, 'metadata.bz2'), 'wb') as fle:
        if SETTINGS['github'] and posthook['github']:
            handle_github(project, branch, system, fsdate, metadata)
        fle.write(bz2.compress(json.dumps(metadata).encode('UTF-8')))
        if os.path.lexists(currentpath):
            os.unlink(currentpath)
        os.symlink(fsdate, currentpath)
        print("[SAVED] {}".format(project))

def validate_dict(dictionary, model):
    '''validate dictionary using model'''
    for key, value in dictionary.items():
        if key not in model:
            raise ValueError("model does not contain key '{}'".format(key))
        if not isinstance(value, type(model[key])):
            return False
        if isinstance(value, dict) and not validate_dict(value, model[key]):
            return False
    return True

def validate_status_codes(dictionary):
    '''validate status codes in dictionary'''
    for key, value in dictionary.items():
        if key == 'analyze' or key not in STUSKEYS:
            continue
        if -1 < value['status'] > 1:
            return False
    return True

def init_dict_using_model(dictionary, model):
    '''set unset values from model dictionary'''
    for key, value in model.items():
        if key not in dictionary or (not dictionary[key] and not isinstance(dictionary[key], (int, float, complex))):
            dictionary[key] = value
        if isinstance(value, dict) and isinstance(dictionary[key], dict):
            init_dict_using_model(dictionary[key], value)

@route('/build/<project>/<branch>/<system>', ['POST'])
def got_build(project=None, branch=None, system=None):
    '''got build data from client'''
    if not is_authenticated_for_project(project):
        abort(401, 'Not authorized.')

    try:
        data = request.json
    except ValueError:
        data = None

    if data:
        init_dict_using_model(data, BUILDJSONMDL)

    if data is None or not validate_dict(data, BUILDJSONMDL) or not validate_status_codes(data):
        abort(400, 'Bad JSON, expected: {\n' \
               '"upstream":"upstream url",\n' \
               '"client":"client name (computer)",\n' \
               '"commit":"commit sha",\n' \
               '"force":true/false,\n' \
               '"description":"commit description",\n' \
               '"build":{"status":-1/0/1, "log":"base64"},\n' \
               '"test":{"status":-1/0/1, "log":"base64"},\n' \
               '"package":{"status":-1/0/1, "log":"base64", "zip":"base64"},\n' \
               '"analyze":{"status":number of warnings, "log":"base64"},\n' \
               '"github":{"user":"github user", "repo":"github repository"}\n' \
               '}\n' \
               'status -1 == skipped\nstatus  0 == failed\nstatus  1 == OK\n' \
               'force replaces build if already submitted for the commit\n' \
               'logs and files should be base64 encoded\n' \
               'specify github for post-hook issues\n')

    save_build(project, branch, system, data)
    return 'OK!'

@route('/build/<project>', ['DELETE'])
def delete_project(project=None):
    '''got project delete request from client'''
    if not is_authenticated_for_project(project):
        abort(401, 'Not authorized.')
    if not delete_build(project):
        abort(400, 'Project does not exist.')
    return 'OK!'

@route('/build/<project>/<branch>', ['DELETE'])
def delete_branch(project=None, branch=None):
    '''got branch delete request from client'''
    if not is_authenticated_for_project(project):
        abort(401, 'Not authorized.')
    if not delete_build(project, branch):
        abort(400, 'Branch does not exist.')
    return 'OK!'

@route('/build/<project>/<branch>/<system>', ['DELETE'])
def delete_system(project=None, branch=None, system=None):
    '''got branch delete request from client'''
    if not is_authenticated_for_project(project):
        abort(401, 'Not authorized.')
    if not delete_build(project, branch, system):
        abort(400, 'System does not exist.')
    return 'OK!'

@route('/build/<project>/<branch>/<system>/<fsdate>', ['DELETE'])
def delete_fsdate(project=None, branch=None, system=None, fsdate=None):
    '''got branch delete request from client'''
    if not is_authenticated_for_project(project):
        abort(401, 'Not authorized.')
    if not delete_build(project, branch, system, fsdate):
        abort(400, 'System does not exist.')
    return 'OK!'

@route('/build/<project>/<branch>/<system>/<fsdate>/<bfile>')
def get_build_file(project=None, branch=None, system=None, fsdate=None, bfile=None):
    '''get file for build'''
    validate_build(project, branch, system)

    ext = os.path.splitext(bfile)[1]
    path = os.path.join(SETTINGS['builds_directory'], project)
    path = os.path.join(path, branch)
    path = os.path.join(path, system)
    path = os.path.join(path, fsdate)

    if not os.path.exists(path):
        abort(404, "Build does not exist.")

    if bfile == 'build-status.png':
        response.set_header('Cache-control', 'no-cache')
        response.set_header('Pragma', 'no-cache')
        if not failure_for_build(project, branch, system, fsdate):
            return static_file('ok.png', root='media/status/')
        return static_file('fail.png', root='media/status/')
    elif ext == '.zip':
        return static_file(bfile, root=path)
    elif ext == '.bz2':
        return static_file(bfile, root=path)
    elif ext == '.txt':
        response.content_type = 'text/plain'
        path = os.path.join(path, bfile.replace('.txt', '.bz2'))
        if os.path.exists(path):
            return bz2.BZ2File(path).read()

    abort(404, 'No such file.')

@route('/build/<project>/<branch>/<system>/<bfile>')
def get_build_file_short(project=None, branch=None, system=None, bfile=None):
    '''short version of get build file'''
    return get_build_file(project, branch, system, 'current', bfile)

@route('/platform/<bfile>')
def get_platform_icon(bfile=None):
    '''get platform icon'''
    return static_file(bfile, root='media/platform/')

def absolute_link(relative, https=False):
    '''turn relative link to absolute'''
    host = request.get_header('host')
    if not host:
        return '#'
    return '{}://{}/{}'.format('https' if https else 'http', host, relative)

def parse_status_for_metadata(metadata):
    '''parse human readable result for status'''
    for key in STUSKEYS:
        if key == 'analyze' and metadata[key]['status'] >= 0:
            metadata[key]['result'] = str(metadata[key]['status'])
        else:
            metadata[key]['result'] = SCODEMAP[metadata[key]['status']]

def failure_for_metadata(metadata):
    '''get failure status for metadata'''
    for key, value in metadata.items():
        if key == 'analyze' or key not in STUSKEYS:
            continue
        if value['status'] == 0:
            return True
    return False

def date_for_metadata(metadata):
    '''get date for metadata'''
    return datetime.strptime(metadata['date'], "%Y-%m-%dT%H:%M:%S.%f")

def fsdate_for_metadata(metadata):
    '''get fsdate for metadata'''
    date = date_for_metadata(metadata)
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%f")

def parse_status_for_build(project, branch, system, fsdate):
    '''parse human readable result for build'''
    return parse_status_for_metadata(metadata_for_build(project, branch, system, fsdate))

def failure_for_build(project, branch, system, fsdate):
    '''get failure status for build'''
    return failure_for_metadata(metadata_for_build(project, branch, system, fsdate))

def date_for_build(project, branch, system, fsdate):
    '''get date for build'''
    return date_for_metadata(metadata_for_build(project, branch, system, fsdate))

def fsdate_for_build(project, branch, system, fsdate):
    '''get fsdate for build'''
    return fsdate_for_metadata(metadata_for_build(project, branch, system, fsdate))

def parse_links_for_build(project, branch, system, fsdate, metadata):
    '''get status links array for build'''
    systempath = os.path.join(SETTINGS['builds_directory'], project, branch, system, fsdate)

    for key in STUSKEYS:
        if os.path.exists(os.path.join(systempath, '{}-log.bz2'.format(key))):
            metadata[key]['url'] = quote('/build/{}/{}/{}/{}/{}-log.txt'.format(project, branch, system, fsdate, key))
        else:
            metadata[key]['url'] = '#'

def status_image_link_for_build(project, branch, system, fsdate):
    '''get status image for build'''
    import time
    return '{}?{}'.format(quote('/build/{}/{}/{}/{}/build-status.png'.format(project, branch, system, fsdate)), time.time())

def metadata_for_build(project, branch, system, fsdate):
    '''get metadata for build'''
    metadata = {}
    path = os.path.join(SETTINGS['builds_directory'], project, branch, system, fsdate, 'metadata.bz2')
    if os.path.exists(path):
        try:
            bz2data = bz2.BZ2File(path).read()
        except EOFError:
            bz2data = None
        if bz2data:
            metadata = json.loads(bz2data.decode('UTF-8'))
    return metadata

def icon_for_system(system):
    '''get link to icon for system'''
    icon = 'platform/unknown.png'
    if 'linux' in system.lower():
        icon = '/platform/linux.png'
    if 'darwin' in system.lower():
        icon = '/platform/darwin.png'
    if 'win32' in system.lower() or 'win64' in system.lower():
        icon = '/platform/windows.png'
    if 'bsd' in system.lower():
        icon = '/platform/bsd.png'
    return icon

def get_build_data(project, branch, system, fsdate, get_history=True, in_metadata=None):
    '''get data for build'''
    # pylint: disable=too-many-arguments

    metadata = {}
    if in_metadata:
        for key, value in in_metadata.items():
            metadata[key] = value
    else:
        metadata = metadata_for_build(project, branch, system, fsdate)
    if not metadata:
        return None
    date = date_for_metadata(metadata)
    if not date:
        return None

    for key in STUSKEYS:
        if key not in metadata:
            metadata[key] = {'status': -1}

    metadata['project'] = project
    metadata['fsdate'] = fsdate
    metadata['idate'] = date
    metadata['fdate'] = date.strftime("%Y-%m-%d %H:%M")
    metadata['system'] = system
    metadata['branch'] = branch
    metadata['systemimage'] = icon_for_system(system)
    metadata['statusimage'] = status_image_link_for_build(project, branch, system, fsdate)

    parse_status_for_metadata(metadata)
    parse_links_for_build(project, branch, system, fsdate, metadata)

    if get_history:
        metadata['history'] = []
        systempath = os.path.join(SETTINGS['builds_directory'], project, branch, system)
        current = os.readlink(os.path.join(systempath, 'current'))
        for old_fsdate in sorted(os.listdir(systempath), reverse=True):
            if old_fsdate == fsdate or old_fsdate == current or old_fsdate == 'current':
                continue
            old = get_build_data(project, branch, system, old_fsdate, get_history=False)
            if not old:
                continue
            metadata['history'].append(old)

    return metadata

def get_projects():
    '''get projects for index page'''
    if not os.path.isdir(SETTINGS['builds_directory']):
        return []

    projects = []
    for project in os.listdir(SETTINGS['builds_directory']):
        projects.append({'name': project, 'url': None, 'date': None, 'builds': []})
        projectpath = os.path.join(SETTINGS['builds_directory'], project)
        for branch in os.listdir(projectpath):
            branchpath = os.path.join(projectpath, branch)
            for system in os.listdir(branchpath):
                data = get_build_data(project, branch, system, 'current')
                if not data:
                    continue
                if not projects[-1]['date'] or data['idate'] > projects[-1]['date']:
                    projects[-1]['date'] = data['idate']
                    if 'upstream' in data:
                        projects[-1]['url'] = data['upstream']
                projects[-1]['builds'].append(data)
        if projects[-1]['date']:
            projects[-1]['builds'] = sorted(projects[-1]['builds'], key=lambda k: k['date'], reverse=True)
        else:
            projects.remove(projects[-1])

    projects = sorted(projects, key=lambda k: k['date'], reverse=True)
    return projects

def clean_build_json(build):
    '''clean build data for json dump'''
    build['date'] = build['fdate']
    del build['idate']
    del build['fdate']
    if 'history' in build:
        for old in build['history']:
            clean_build_json(old)
    return build

@route('/delete/<project>/<branch>/<system>/<fsdate>', ['GET'])
def delete_build_ui(project=None, branch=None, system=None, fsdate=None):
    '''delete build using get interface'''
    admin = True if request.environ.get('REMOTE_ADDR') == '127.0.0.1' else False
    if not admin:
        abort(403, 'You are not allowed to do this')
    delete_build(project, branch, system, fsdate)
    if is_json_request():
        return 'OK!'
    if build_exists(project, branch, system):
        return redirect('/build/{}/{}/{}'.format(project, branch, system))
    return redirect('/')

@route('/build/<project>/<branch>/<system>', ['GET'])
def system_page(project=None, branch=None, system=None):
    '''got branch delete request from client'''
    validate_build(project, branch, system)
    data = get_build_data(project, branch, system, 'current')
    if not data:
        abort(404, 'Builds for system not found')
    if is_json_request():
        return dump_json(clean_build_json(data))
    admin = True if request.environ.get('REMOTE_ADDR') == '127.0.0.1' else False
    return template('build', admin=admin, build=data, standalone=True)

@route('/')
def index():
    '''main page with information of all builds'''
    if is_json_request():
        projects = get_projects()
        for project in projects:
            del project['date']
            for build in project['builds']:
                clean_build_json(build)
        return dump_json(projects)
    admin = True if request.environ.get('REMOTE_ADDR') == '127.0.0.1' else False
    return template('projects', admin=admin, projects=get_projects())

@route('/favicon.ico')
def get_favicon():
    '''fetch favicon'''
    return static_file('favicon.ico', root='.')

def main():
    '''main method'''
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-s', '--server', dest='server',
                      help='bottle.py WSGI server backend')
    parser.add_option('-p', '--port', dest='port',
                      help='server port')
    parser.add_option('-b', '--buildsdir', dest='builds_directory',
                      help='directory for builds')
    optargs = parser.parse_args()

    for key in SETTINGS.keys():
        if optargs[0].__dict__.get(key):
            SETTINGS[key] = optargs[0].__dict__[key]

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run(server=SETTINGS['server'], host='0.0.0.0', port=SETTINGS['port'])

def setup():
    '''setup method'''
    BaseTemplate.defaults['STUSKEYS'] = STUSKEYS

setup()
if __name__ == "__main__":
    main()
else:
    # pylint: disable=invalid-name
    application = bottle.default_app()
    application.catchall = False

#  vim: set ts=8 sw=4 tw=0 :
