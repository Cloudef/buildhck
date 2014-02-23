# pylint: disable=C0103
'''authorization module for buildhck'''

# This dictionary contains authorization keys for projects.
# Leave the key object empty, to allow everything to be pushed to server.
# Leave value for key empty, to allow the project being pushed without key.
# Empty key that contains value is default key for every project.
#
# Example dictionary:
# key = {'glhck': 'mypassword'
#        'public_project': ''
#        '': 'publicpassword'}
#
# Above configuration, would allow to push build information for glhck
# with 'mypassword' used as key in HTTP authorization header.
# Everyone could push to public_project with any key.
# And any project expect glhck could be pushed with 'publicpassword'.
key = {}

# Github authorization token
# You can create this token in your github account managment page
# When enabled, clients can request server to push github issues
github = ''

# Bottle.py WSGI backend
server = 'auto'

# Server port
port = 9001

#  vim: set ts=8 sw=4 tw=0 :
