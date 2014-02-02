#!/usr/bin/env python3
# pylint: disable=C0301, R0911, R0912, R0913, R0914
"""automatic build system client/server framework"""

from lib.bottle import static_file, response, request, delete, abort, post, get, run
from base64 import b64decode
from datetime import datetime
import os, re, bz2, json

SETTINGS = {}
SETTINGS['builds_directory'] = 'builds'
SETTINGS['github'] = {}
SETTINGS['auth'] = {}

STUSKEYS = ['build', 'test', 'package']

BUILDJSONMDL = {'client': 'unknown client', 'commit': 'unknown commit', 'description': '',
                'build': {'status': -1, 'log': ''},
                'test': {'status': -1, 'log': ''},
                'package': {'status': -1, 'log': '', 'zip': ''},
                'github': {'user': '', 'repo': ''}}

FNFILTERPROG = re.compile(r'[:;*?"<>|()\\]')

SCODEMAP = {-1: 'SKIP', 0: 'FAIL', 1: 'OK'}

HTMLSCOD = {-1: '<span style="color:dimgray">SKIP</span>',
             0: '<span style="color:red">FAIL</span>',
             1: '<span style="color:green">OK</span>'}

HTMLHEAD = '<html><head><title>buildhck</title>' \
           '<link rel="shortcut icon" type="image/x-icon" href="/favicon.ico"/>' \
           '<style>' \
           'html { font-size: 100%; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }' \
           'body { margin: 8px; font-size: 12px; line-height: 1.2; }' \
           'body, button, input, select, textarea { font-family:sans-serif; }' \
           'a { color:steelblue; text-decoration:none; }' \
           '</style>' \
           '</head><body><section>'
HTMLFOOT = '</section></body></html>'
HTMLPRJS = '<div><h2>{}</h2>'
HTMLBILD = '<div><p><img src="{}" alt="platform"/><strong>{}</strong> on <strong>{}</strong><br/>' \
           '{} @ {}<br/>{}' \
           '{} UTC<br/>' \
           '<a href="{}">build</a> {} <a href="{}">tests</a> {} <a href="{}">package</a> {}<br/>' \
           '<img src="{}" alt="status"/></p></div>'
HTMLPRJE = '</div>'

ISSUESBJ = '[buildhck] Automated build failed'
ISSUEBDY = '![platform icon]({}) **{}** on **{}**\n' \
           '{} @ {}\n{}' \
           '{} UTC\n' \
           '[build]({}) {} [tests]({}) {} [package]({}) {}'

try:
    import authorization
    SETTINGS['auth'] = authorization.key
    SETTINGS['github'] = authorization.github
except ImportError as exc:
    print("Authorization module was not loaded!")

def validate_build(project, branch=None, system=None):
    """validate build information"""
    if FNFILTERPROG.search(project):
        abort(400, 'project name contains invalid characters (invalid: :;*?"<>|()\\)')
    if branch and FNFILTERPROG.search(branch):
        abort(400, 'branch name contains invalid characters (invalid: :;*?"<>|()\\)')
    if system and FNFILTERPROG.search(system):
        abort(400, 'system name contains invalid characters (invalid: :;*?"<>|()\\)')

def is_authenticated_for_project(project):
    """is client authenticated to send build information"""
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
    """safe mkdir"""
    if not os.path.exists(sdir):
        os.mkdir(sdir)
    if not os.path.isdir(sdir):
        raise IOError("local path '{}' is not a directory".format(sdir))

def github_issue(user, repo, subject, body, issueid=None, close=False):
    """create/comment/delete github issue"""
    if not SETTINGS['github']:
        print("no github_token specified, won't handle issue request")
        return None

    if close and not issueid:
        print("can't close github issue without id")
        return None

    from urllib.parse import quote
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
        issueid = json.load(srvdata)['number']
        print("[GITHUB] issue created ({})".format(issueid))
    else:
        print("[GITHUB] issue updated ({})".format(issueid))

    return issueid if not close else None

def handle_github(project, branch, system, metadata):
    """handle github posthook for build"""
    github = metadata['github']

    if 'issueid' not in github:
        github['issueid'] = None

    failed = failure_for_metadata(metadata)

    if not github or (not failed and not github['issueid']):
        return # nothing to do

    desc = ''
    if metadata['description']:
        desc = "{}\n".format(metadata['description'].splitlines()[0])

    date = date_for_metadata(metadata)
    url = links_for_build(project, branch, system)
    status = status_for_metadata(metadata)
    for idx in range(len(url)):
        url[idx] = absolute_link(url[idx])

    subject = ISSUESBJ
    body = ISSUEBDY.format(absolute_link(icon_for_system(system)), system, metadata['client'],
                           branch, metadata['commit'],
                           desc,
                           date.strftime("%Y-%m-%d %H:%M"),
                           url[0], status[0], url[1], status[1], url[2], status[2])

    github['issueid'] = github_issue(github['user'], github['repo'], subject, body, github['issueid'], not failed)

def check_github_posthook(data, metadata):
    """check if github posthook should be used"""
    if not data['github'] or not data['github']['user'] or not data['github']['repo']:
        return False

    issueid = None
    if 'github' in metadata and metadata['github'] and 'issueid' in metadata['github']:
        issueid = metadata['github']['issueid']

    metadata['github'] = {'user': data['github']['user'],
                          'repo': data['github']['repo'],
                          'issueid': issueid}
    return True

def delete_build(project, branch=None, system=None):
    """delete build"""
    validate_build(project, branch, system)

    parentpath = None
    buildpath = os.path.join(SETTINGS['builds_directory'], project)
    if branch:
        parentpath = buildpath
        buildpath = os.path.join(buildpath, branch)
    if system:
        parentpath = buildpath
        buildpath = os.path.join(buildpath, system)
    if not os.path.isdir(buildpath):
        return False

    import shutil
    shutil.rmtree(buildpath)
    if system and not os.listdir(parentpath):
        delete_build(project, branch)
    if branch and not system and not os.listdir(parentpath):
        delete_build(project)
    return True

def save_build(project, branch, system, data):
    """save build to disk"""
    validate_build(project, branch, system)
    if not data:
        raise ValueError('build should have data')

    s_mkdir(SETTINGS['builds_directory'])
    buildpath = os.path.join(SETTINGS['builds_directory'], project)
    s_mkdir(buildpath)
    buildpath = os.path.join(buildpath, branch)
    s_mkdir(buildpath)
    buildpath = os.path.join(buildpath, system)
    s_mkdir(buildpath)

    metadata = metadata_for_build(project, branch, system)
    metadata['date'] = datetime.utcnow().isoformat()
    metadata['client'] = data['client']
    metadata['commit'] = data['commit']
    metadata['description'] = data['description']

    posthook = {}
    posthook['github'] = check_github_posthook(data, metadata)

    for key, value in data.items():
        if key not in STUSKEYS:
            continue

        metadata[key] = {'status': value['status']}

        if value['log']:
            buildlog = bz2.compress(b64decode(value['log'].encode('UTF-8')))
            with open(os.path.join(buildpath, '{}-log.bz2'.format(key)), 'wb') as fle:
                fle.write(buildlog)

        if key == 'package' and value['zip']:
            buildzip = b64decode(value['zip'].encode('UTF-8'))
            with open(os.path.join(buildpath, 'package.zip'), 'wb') as fle:
                fle.write(buildzip)

    with open(os.path.join(buildpath, 'metadata.bz2'), 'wb') as fle:
        if SETTINGS['github'] and posthook['github']:
            handle_github(project, branch, system, metadata)
        fle.write(bz2.compress(json.dumps(metadata).encode('UTF-8')))
        print("[SAVED] {}".format(project))

def validate_dict(dictionary, model):
    """validate dictionary using model"""
    for key, value in dictionary.items():
        if key not in model:
            raise ValueError("model does not contain key '{}'".format(key))
        if not isinstance(value, type(model[key])):
            return False
        if isinstance(value, dict) and not validate_dict(value, model[key]):
            return False
    return True

def validate_status_codes(dictionary):
    """validate status codes in dictionary"""
    for key, value in dictionary.items():
        if key not in STUSKEYS:
            continue
        if -1 < value['status'] > 1:
            return False
    return True

def init_dict_using_model(dictionary, model):
    """set unset values from model dictionary"""
    for key, value in model.items():
        if key not in dictionary or (not dictionary[key] and not isinstance(dictionary[key], (int, float, complex))):
            dictionary[key] = value
        if isinstance(value, dict):
            init_dict_using_model(dictionary[key], value)

@post('/build/:project/:branch/:system')
def got_build(project=None, branch=None, system=None):
    """got build data from client"""
    if not is_authenticated_for_project(project):
        abort(401, 'Not authorized.')

    try:
        data = request.json
    except ValueError:
        data = None

    if data:
        init_dict_using_model(data, BUILDJSONMDL)

    if data is None or not validate_dict(data, BUILDJSONMDL) or not validate_status_codes(data):
        abort(400, 'Bad JSON, expected: {' \
               '"client":"client name (computer)", ' \
               '"commit":"commit sha", ' \
               '"description":"commit description", ' \
               '"build":{status:-1/0/1, log:"base64"}, ' \
               '"test":{status:-1/0/1, log:"base64"}, ' \
               '"package":{"status":-1/0/1, "log":"base64", "zip":"base64"},' \
               '"github":{"user":"", "repo":""}' \
               '}\n' \
               'status -1 == skipped\nstatus  0 == failed\nstatus  1 == OK\n' \
               'logs should be base64 encoded\n' \
               'zip package should be base64 encoded\n' \
               'specify github for post-hook issues\n')

    save_build(project, branch, system, data)
    return 'OK!'

@delete('/build/:project')
def delete_project(project=None):
    """got project delete request from client"""
    if not is_authenticated_for_project(project):
        abort(401, 'Not authorized.')
    if not delete_build(project):
        abort(400, 'Project does not exist.')
    return 'OK!'

@delete('/build/:project/:branch')
def delete_branch(project=None, branch=None):
    """got branch delete request from client"""
    if not is_authenticated_for_project(project):
        abort(401, 'Not authorized.')
    if not delete_build(project, branch):
        abort(400, 'Branch does not exist.')
    return 'OK!'

@delete('/build/:project/:branch/:system')
def delete_system(project=None, branch=None, system=None):
    """got branch delete request from client"""
    if not is_authenticated_for_project(project):
        abort(401, 'Not authorized.')
    if not delete_build(project, branch, system):
        abort(400, 'System does not exist.')
    return 'OK!'

@get('/build/:project/:branch/:system/:bfile')
def get_build_file(project=None, branch=None, system=None, bfile=None):
    """get file for build"""
    validate_build(project, branch, system)

    ext = os.path.splitext(bfile)[1]
    path = os.path.join(SETTINGS['builds_directory'], project)
    path = os.path.join(path, branch)
    path = os.path.join(path, system)

    if not os.path.exists(path):
        abort(404, "Build does not exist.")

    if bfile == 'build-status.png':
        if not failure_for_build(project, branch, system):
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

@get('/platform/:bfile')
def get_platform_icon(bfile=None):
    """get platform icon"""
    return static_file(bfile, root='media/platform/')

def absolute_link(relative, https=False):
    """turn relative link to absolute"""
    host = request.get_header('host')
    if not host:
        return '#'
    return '{}://{}/{}'.format('https' if https else 'http', host, relative)

def status_for_metadata(metadata, html=False):
    """get status array for metadata"""
    if not metadata:
        return None
    table = SCODEMAP if not html else HTMLSCOD
    status = [table[metadata['build']['status']],
              table[metadata['test']['status']],
              table[metadata['package']['status']]]
    return status

def failure_for_metadata(metadata):
    """get failure status for metadata"""
    if not metadata:
        return False
    for key, value in metadata.items():
        if key not in STUSKEYS:
            continue
        if value['status'] == 0:
            return True
    return False

def date_for_metadata(metadata):
    """get date for metadata"""
    if not metadata:
        return None
    return datetime.strptime(metadata['date'], "%Y-%m-%dT%H:%M:%S.%f")

def status_for_build(project, branch, system, html=False):
    """get status array for build"""
    return status_for_metadata(metadata_for_build(project, branch, system), html)

def failure_for_build(project, branch, system):
    """get failure status for build"""
    return failure_for_metadata(metadata_for_build(project, branch, system))

def date_for_build(project, branch, system):
    """get date for build"""
    return date_for_metadata(metadata_for_build(project, branch, system))

def links_for_build(project, branch, system):
    """get status links array for build"""
    url = ['#', '#', '#']
    systempath = os.path.join(SETTINGS['builds_directory'], project, branch, system)
    if os.path.exists(os.path.join(systempath, 'build-log.bz2')):
        url[0] = 'build/{}/{}/{}/build-log.txt'.format(project, branch, system)
    if os.path.exists(os.path.join(systempath, 'test-log.bz2')):
        url[1] = 'build/{}/{}/{}/test-log.txt'.format(project, branch, system)
    if os.path.exists(os.path.join(systempath, 'package-log.bz2')):
        url[2] = 'build/{}/{}/{}/package-log.txt'.format(project, branch, system)
    return url

def status_image_link_for_build(project, branch, system):
    """get status image for build"""
    return 'build/{}/{}/{}/build-status.png'.format(project, branch, system)

def metadata_for_build(project, branch, system):
    """get metadata for build"""
    metadata = {}
    path = os.path.join(SETTINGS['builds_directory'], project, branch, system, 'metadata.bz2')
    if os.path.exists(path):
        bz2data = bz2.BZ2File(path).read()
        if bz2data:
            metadata = json.loads(bz2data.decode('UTF-8'))
    return metadata

def icon_for_system(system):
    """get link to icon for system"""
    icon = 'platform/unknown.png'
    if 'linux' in system.lower():
        icon = 'platform/linux.png'
    if 'darwin' in system.lower():
        icon = 'platform/darwin.png'
    if 'win32' in system.lower() or 'win64' in system.lower():
        icon = 'platform/windows.png'
    if 'bsd' in system.lower():
        icon = 'platform/bsd.png'
    return icon

def html_for_build(project, branch, system):
    """get html for build"""
    metadata = metadata_for_build(project, branch, system)
    if not metadata:
        return

    htmldesc = ''
    if metadata['description']:
        htmldesc = "{}<br/>".format(metadata['description'].splitlines()[0])

    statusimage = status_image_link_for_build(project, branch, system)
    status = status_for_metadata(metadata, True)
    url = links_for_build(project, branch, system)
    date = date_for_metadata(metadata)
    html = HTMLBILD.format(icon_for_system(system), system, metadata['client'],
                           branch, metadata['commit'],
                           htmldesc,
                           date.strftime("%Y-%m-%d %H:%M"),
                           url[0], status[0], url[1], status[1], url[2], status[2],
                           statusimage)
    return html

def build_html_from_projects():
    """build html from projects"""
    if not os.path.isdir(SETTINGS['builds_directory']):
        return ['<h2>No builds</h2>']

    projects = []
    for project in os.listdir(SETTINGS['builds_directory']):
        projects.append({'name': project, 'date': None, 'builds': []})
        projectpath = os.path.join(SETTINGS['builds_directory'], project)
        for branch in os.listdir(projectpath):
            branchpath = os.path.join(projectpath, branch)
            for system in os.listdir(branchpath):
                date = date_for_build(project, branch, system)
                if not projects[-1]['date'] or date > projects[-1]['date']:
                    projects[-1]['date'] = date
                projects[-1]['builds'].append({'html': html_for_build(project, branch, system), 'date': date})
        projects[-1]['builds'] = sorted(projects[-1]['builds'], key=lambda k: k['date'], reverse=True)

    projects = sorted(projects, key=lambda k: k['date'], reverse=True)

    if not projects:
        return ['<h2>No builds</h2>']

    html = []
    for project in projects:
        html.append(HTMLPRJS.format(project['name']))
        for build in project['builds']:
            html.extend(build['html'])
        html.append(HTMLPRJE)
    return html

@get('/')
def index():
    """main page with information of all builds"""
    html = [HTMLHEAD]
    html.extend(build_html_from_projects())
    html.append(HTMLFOOT)
    return ''.join(html)

@get('/favicon.ico')
def get_favicon():
    """fetch favicon"""
    return static_file('favicon.ico', root='.')

run(host='0.0.0.0', port=9001)

#  vim: set ts=8 sw=4 tw=0 :
