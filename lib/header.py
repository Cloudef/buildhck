#!/usr/bin/env python3
# pylint: disable=too-many-locals, missing-docstring

# The author disclaims copyright to this source code.  In place of a legal
# notice, here is a blessing:
#
#    May you do good and not evil.
#    May you find forgiveness for yourself and forgive others.
#    May you share freely, never taking more than you give.
#
# It is based on a snipped found in this project:
#   https://github.com/martinblech/mimerender

def parse_accept(accept):
    '''
    Parse the Accept header *accept*, returning a list with 3-tuples of
    [(str(media_type), dict(params), float(q_value)),] ordered by q values.

    If the accept header includes vendor-specific types like::

        application/vnd.yourcompany.yourproduct-v1.1+json

    It will actually convert the vendor and version into parameters and
    convert the content type into `application/json` so appropriate content
    negotiation decisions can be made.

    Default `q` for values that are not specified is 1.0
    '''

    result = []
    for media_range in accept.split(","):
        parts = media_range.split(";")
        media_type = parts.pop(0).strip()
        media_params = []
        # convert vendor-specific content types into something useful (see
        # docstring)
        typ, subtyp = media_type.split('/')
        # check for a + in the sub-type
        if '+' in subtyp:
            # if it exists, determine if the subtype is a vendor-specific type
            vnd, dummy_sep, extra = subtyp.partition('+')
            if vnd.startswith('vnd'):
                # and then... if it ends in something like "-v1.1" parse the
                # version out
                version = None
                if '-v' in vnd:
                    vnd, dummy_sep, rest = vnd.rpartition('-v')
                    if len(rest):
                        # add the version as a media param
                        try:
                            version = media_params.append(('version',
                                                           float(rest)))
                        except ValueError:
                            version = 1.0 # could not be parsed
                # add the vendor code as a media param
                media_params.append(('vendor', vnd, version))
                # and re-write media_type to something like application/json so
                # it can be used usefully when looking up emitters
                media_type = '{}/{}'.format(typ, extra)
        qal = 1.0
        for part in parts:
            (key, value) = part.lstrip().split("=", 1)
            key = key.strip()
            value = value.strip()
            if key == "qal":
                qal = float(value)
            else:
                media_params.append((key, value))
        result.append((media_type, dict(media_params), qal))
    result.sort(key=lambda x: -x[2])
    return result

def supported_request(header, supported):
    '''Returns most prefered request that is supported'''
    data = parse_accept(header)
    for accept in data:
        if accept[0] in supported:
            return accept[0]
    return None

def parse_accept_language(header):
    '''Parse accept language header'''
    locale_q_pairs = []
    languages = header.split(',')
    for language in languages:
        if language.split(';')[0] == language:
            locale_q_pairs.append((language.strip(), '1'))
        else:
            locale = language.split(';')[0].strip()
            qual = language.split(';')[1].split('=')[1]
            locale_q_pairs.append((locale, qual))
    return locale_q_pairs

def supported_language(header, supported):
    '''Returns most prefered language that is supported'''
    data = parse_accept_language(header)
    for lang in data:
        if lang[0] in supported:
            return lang[0]
    return None

#  vim: set ts=8 sw=4 tw=0 :
