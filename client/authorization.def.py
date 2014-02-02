# pylint: disable=C0103
"""authorization module for buildhck client"""

# This dictionary contains authorization keys for projects.
# Leave the key object empty, to specify default authorization key.
#
# Example dictionary:
# key = {'glhck': 'mypassword'
#        '': 'publicpassword'}
#
# Above configuration, would use 'mypassword' HTTP authorization header
# when pushing build information for glhck project.
# Authorization key 'publicpassword' is used for everything else.
key = {}

# Server address
server = 'http://localhost:9001'

#  vim: set ts=8 sw=4 tw=0 :
