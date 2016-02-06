# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import re

url_scanner = re.Scanner([
    (r'[0-9]+', lambda s,t: 0),
    (r'.', lambda s,t: t),
    ])

def tokenize_url(url):
    """
    Tokenizes the url, making it suitable for storage
    and matching against a :class:`PrefTree`.

    >>> tokenize_url(u'abcd')
    [u'a', u'b', u'c', u'd']
    >>> tokenize_url(u'sum41')
    [u's', u'u', u'm', 0]
    >>> tokenize_url(u'h3l10')
    [u'h', 0, u'l', 0]
    """
    results, remainder = url_scanner.scan(url)
    return results

