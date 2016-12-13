# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from requests.compat import urlparse
from requests.compat import urlencode
from urlparse import parse_qs
import re

url_scanner = re.Scanner([
    (r'[0-9]+', lambda s,t: 0),
    (r'.', lambda s,t: t),
    ])

resolver_domains = ['dx.doi.org','doi.org','hdl.handle.net']
protocol_re = re.compile(r'^([a-z]*:)?//')
domain_re = re.compile(r'^([a-zA-Z0-9-.]*)((:[0-9]+)?(/.*)?)$')
session_parameter_re = re.compile(r'(.*sessionid.*|utm_.*)')

def cleanup_parameters(querystring):
    """
    Removes session-specific arguments (such as jsessionid,
    phpsessionid or utm_source)

    >>> cleanup_parameters('q=test&phpsessionid=a342cb4f')
    'q=test'
    >>> cleanup_parameters('page=3&utm_source=twitter.com')
    'page=3'
    """
    args = parse_qs(querystring)
    filtered_args = filter(
        lambda (k, v): session_parameter_re.match(k) is None,
        args.items())
    sorted_args = sorted(
        filtered_args,
        key=lambda (k, v): k)
    cleaned_args = urlencode(dict(sorted_args), doseq=True)
    return cleaned_args


def prepare_url(url):
    """
    Prepares a URL to be fed, removing the protocol and reversing the
    domain name.

    >>> prepare_url(u'http://dissem.in/faq')
    [u'.in', u'.dissem', u'/', u'f', u'a', u'q']
    >>> prepare_url(u'//gnu.org')
    [u'.org', u'.gnu']
    >>> prepare_url(u'https://duckduckgo.com/?q=test')
    [u'.com', u'.duckduckgo', u'/', u'?', u'q', u'=', u't', u'e', u's', u't']
    >>> prepare_url(u'http://umas.edu:80/abs')
    [u'.edu', u'.umas', u':80', u'/', u'a', u'b', u's']
    >>> prepare_url(u'http://umas.AC.uk/pdf')
    [u'.uk', u'.ac', u'.umas', u'/', u'p', u'd', u'f']
    >>> prepare_url(u'//localhost:8000/t')
    [u'.localhost', u':8000', u'/', u't']
    >>> prepare_url(None)
    >>> prepare_url(u'http://dx.doi.org/10.3406/134')
    [u'.org', u'.doi', u'.dx', u'/', u'10.3406', u'/', 0]
    >>> prepare_url('http://hdl.handle.net/10985/7376')
    [u'.net', u'.handle', u'.hdl', u'/', u'10985', u'/', 0]
    >>> prepare_url('//gnu.org/?utm_source=twitter&jsessionid=e452fb1')
    [u'.org', u'.gnu', u'/']
    """
    if not url:
        return url
    url = url.strip()

    parsed = urlparse(url)

    cleaned_params = cleanup_parameters(parsed.params)
    cleaned_query = cleanup_parameters(parsed.query)

    split_by_port = parsed.netloc.split(':')
    reversed_domain = ['.'+dom.lower() for dom in
                       reversed(split_by_port[0].split('.'))]
    if len(split_by_port) > 1:
        reversed_domain.append(':'+split_by_port[1])

    # do not tokenize DOIs or HANDLES as the numbers they contain can be significant
    # to guess full text availability
    if parsed.netloc in resolver_domains:
        parts = parsed.path.split('/')
        url_path = ['/']
        if len(parts) > 1:
            url_path += [parts[1], '/'] + tokenize_url_path('/'.join(parts[2:]))
    # otherwise, tokenize
    else:
        orig_path = parsed.path
        if cleaned_params:
            orig_path += ';'+cleaned_params
        if cleaned_query:
            orig_path += '?'+cleaned_query
        url_path = tokenize_url_path(orig_path)

    return reversed_domain + url_path


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

