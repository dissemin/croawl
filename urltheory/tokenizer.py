# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import re

url_scanner = re.Scanner([
    (r'[0-9]+', lambda s,t: 0),
    (r'.', lambda s,t: t),
    ])

protocol_re = re.compile(r'^[a-z]*://')
domain_re = re.compile(r'^([a-zA-Z0-9-.]*)((:[0-9]+)?/.*)$')
def prepare_url(url):
    """
    Prepares a URL to be fed, removing the protocol and reversing the
    domain name.

    >>> prepare_url(u'http://dissem.in/faq')
    [u'.in', u'.dissem', u'/', u'f', u'a', u'q']
    >>> prepare_url(u'https://duckduckgo.com/?q=test')
    [u'.com', u'.duckduckgo', u'/', u'?', u'q', u'=', u't', u'e', u's', u't']
    >>> prepare_url(u'http://umas.edu:80/abs')
    [u'.edu', u'.umas', u':', 0, u'/', u'a', u'b', u's']
    >>> prepare_url(None)
    >>> prepare_url(u'http://bad_/test')
    [u'_', u'b', u'a', u'd', u'_', u'/', u't', u'e', u's', u't']
    """
    if not url:
        return url
    url = url.strip()
    url = protocol_re.sub('', url)
    match = domain_re.match(url)
    if not match:
        return ['_']+tokenize_url_path(url)
    reversed_domain = ['.'+dom for dom in reversed(match.group(1).split('.'))]
    return reversed_domain + tokenize_url_path(match.group(2))



def tokenize_url_path(url):
    """
    Tokenizes the url, making it suitable for storage
    and matching against a :class:`PrefTree`.

    >>> tokenize_url_path(u'abcd')
    [u'a', u'b', u'c', u'd']
    >>> tokenize_url_path(u'sum41')
    [u's', u'u', u'm', 0]
    >>> tokenize_url_path(u'h3l10')
    [u'h', 0, u'l', 0]
    """
    results, remainder = url_scanner.scan(url)
    return results

