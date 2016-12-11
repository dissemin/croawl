# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from math import log
from urltheory.utils import *

def binary_entropy(p):
    return -(p*log(p,2)+(1-p)*log(1-p,2))

def confidence(url_count, success_count):
    """
    Returns 1 - binary_entropy(smoothed_probability)
    """
    smoothed_probability = (1.+success_count)/(2.+url_count)
    return 1. - binary_entropy(smoothed_probability)


class WildcardCharacter(object):
    """
    An object representing a wildcard in a string.
    This is used to generate the URLs of a :class:`PrefTree`
    that thas been pruned.
    This character should not be part of the labels of branches
    in a tree (use PrefTree.is_wildcard instead).
    """
    def __unicode__(self):
        return '*'

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
    [u'h', u'i']
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

