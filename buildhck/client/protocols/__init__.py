# pylint: disable=line-too-long
'''package containing modules for the different protocols we support'''

class NothingToDoException(Exception):
    '''expection raised when there is nothing to cook, if this fails nothing is sent'''


class DownloadException(Exception):
    '''expection raised when there was problem with download, if this fails nothing is sent'''
