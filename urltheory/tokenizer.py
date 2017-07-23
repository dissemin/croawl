# -*- encoding: utf-8 -*-

from requests.compat import urlparse
from requests.compat import urlencode
from urllib.parse import parse_qs
from urllib.parse import urlunparse
import re

url_scanner = re.Scanner([
    (r'\d+', lambda s,t: 0),
    (r'.', lambda s,t: t),
    ])

resolver_domains = ['dx.doi.org','doi.org','hdl.handle.net']
protocol_re = re.compile(r'^([a-z]*:)?//')
domain_re = re.compile(r'^([a-zA-Z0-9-.]*)((:[0-9]+)?(/.*)?)$')
session_parameter_re = re.compile(r'(.*sess(ion)?id.*|utm_.*)')

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
    filtered_args = [k_v for k_v in list(args.items()) if session_parameter_re.match(str(k_v[0])) is None]
    cleaned_args = urlencode(dict(filtered_args), doseq=True)
    return cleaned_args

def normalize_url(url):
    """
    Removes protocol, cleans up parameters

    >>> normalize_url(u'https://doai.io/?phpsessid=2ef491a3d2&q=test#body')
    '//doai.io/?q=test'
    """
    if not url:
        return url
    parsed = urlparse(url)
    cleaned_params = cleanup_parameters(parsed.params)
    cleaned_query = cleanup_parameters(parsed.query)
    return urlunparse(
        ('',
        parsed.netloc,
        parsed.path,
        cleaned_params,
        cleaned_query,
        ''))

def flatten_to_re(lst, reverse=False):
    """
    Flattens a list of strings, produced by the tokenizer,
    to a regular expression
    """
    tokens = [
        '\d+' if type(x) == int else re.escape(x)
        for x in lst
    ]
    if reverse:
        tokens = reversed(tokens)
    return ''.join(tokens)

def prepare_url(url):
    """
    Prepares a URL to be fed, removing the protocol and reversing the
    domain name.

    >>> prepare_url('http://dissem.in/faq')
    ['.in', '.dissem', '/', 'f', 'a', 'q']
    >>> prepare_url('//gnu.org')
    ['.org', '.gnu']
    >>> prepare_url('https://duckduckgo.com/?q=test')
    ['.com', '.duckduckgo', '/', '?', 'q', '=', 't', 'e', 's', 't']
    >>> prepare_url('http://umas.edu:80/abs')
    ['.edu', '.umas', ':80', '/', 'a', 'b', 's']
    >>> prepare_url('http://umas.AC.uk/pdf')
    ['.uk', '.ac', '.umas', '/', 'p', 'd', 'f']
    >>> prepare_url('//localhost:8000/t')
    ['.localhost', ':8000', '/', 't']
    >>> prepare_url(None)
    >>> prepare_url('http://dx.doi.org/10.3406/134')
    ['.org', '.doi', '.dx', '/', '10.3406', '/', 0]
    >>> prepare_url('http://hdl.handle.net/10985/7376')
    ['.net', '.handle', '.hdl', '/', '10985', '/', 0]
    >>> prepare_url('//gnu.org/?utm_source=twitter&jsessionid=e452fb1')
    ['.org', '.gnu', '/']
    """
    if not url:
        return url
    url = normalize_url(url)

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

    >>> tokenize_url_path('abcd')
    ['a', 'b', 'c', 'd']
    >>> tokenize_url_path('sum41')
    ['s', 'u', 'm', 0]
    >>> tokenize_url_path('h3l10')
    ['h', 0, 'l', 0]
    """
    results, remainder = url_scanner.scan(url)
    return results

