# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from requests.compat import urlparse, urljoin
from requests.utils import requote_uri

def normalize_outgoing_url(orig_url, next_url):
    try:
        if type(orig_url) != str:
            orig_url = orig_url.encode('ascii')
        if type(next_url) != str:
            next_url = next_url.encode('ascii')
    except UnicodeEncodeError:
        return

    if next_url.startswith('//'):
        parsed_orig_url = urlparse(orig_url)
        next_url = '%s:%s' % (parsed_orig_url.scheme, next_url)

    parsed = urlparse(next_url)
    next_url = parsed.geturl()

    if not parsed.netloc:
        next_url = urljoin(orig_url, requote_uri(next_url))
    else:
        next_url = requote_uri(next_url)
    # end adapted code
    return next_url

