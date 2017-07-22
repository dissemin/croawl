# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from math import log
from urltheory.utils import *

def binary_entropy(p):
    if p <= 0. or p >= 1.:
        return 0.
    return -(p*log(p,2)+(1-p)*log(1-p,2))

def proba_confidence(p):
    """
    Returns the confidence of a probability:
    1. - binary_entropy(p)
    """
    return 1. - binary_entropy(p)

def confidence(url_count, success_count, smoothing=(1.,1.)):
    """
    Returns 1 - binary_entropy(smoothed_probability)

    :param smoothing: A pair of floats for the smoothing (succes,failure)

    >>> confidence(10, 5)
    0.0
    >>> confidence(10, 0, smoothing=(0.,0.))
    1.0
    >>> confidence(10, 0, smoothing=(0.,1.))
    1.0
    >>> int(confidence(10, 0, smoothing=(2.,2.))*10)
    4
    >>> int(confidence(10, 9)*10)
    3
    >>> confidence(10, 9) == confidence(10, 1)
    True
    >>> confidence(0, 0)
    0.0
    """
    if url_count < 1:
        return 0.
    smoothed_probability = (smoothing[0]+success_count)/(smoothing[0]+smoothing[1]+url_count)
    return proba_confidence(smoothed_probability)


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
    ''
    >>> flatten([u'a',u'b'])
    u'ab'
    >>> flatten([1,3,5])
    '135'
    """
    res = str('')
    for x in lst:
        if type(x) == int:
            x = str(x)
        res += x
    return res

