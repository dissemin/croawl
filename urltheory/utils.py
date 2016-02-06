# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

def longest_common_prefix(a,b):
    """
    Computes the longest common prefix of two lists `a` and `b`.

    >>> longest_common_prefix([],[])
    []
    >>> longest_common_prefix([1],[2])
    []
    >>> longest_common_prefix([0,1],[0,2,3])
    [0]
    >>> longest_common_prefix(u'hi there', u'himself')
    u'hi'
    """
    idx = 0
    ret = []
    while idx < min(len(a),len(b)) and a[idx] == b[idx]:
        ret.append(a[idx])
        idx += 1
    return ret

def flatten(lst):
    """
    Flattens a list of strings into a string.

    >>> flatten([])
    u''
    >>> flatten([u'a',u'b'])
    u'ab'
    >>> flatten([1,3,5])
    u'135'
    """
    res = ''
    for x in lst:
        res += unicode(x)
    return res


