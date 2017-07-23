# -*- encoding: utf-8 -*-

"""
A smoothing strategy takes raw occurrence
counts from the prefix tree, together with
the length of the corresponding URL prefixes,
and returns smoothed probability estimates.
"""

import math

class SmoothingStrategy(object):
    """
    This is the interface that smoothing strategies
    should implement.
    """

    def evaluate(self, count, success, length):
        """
        Returns a smoothed probability estimate
        given the raw counts supplied. The length
        of the prefix can also be taken into account
        (this amounts to putting a different smoothing
        on each level of the prefix tree).
        """
        raise NotImplemented

class ConstantDirichlet(SmoothingStrategy):
    """
    Put the same Dirichlet prior on the distribution of
    each node

    >>> ConstantDirichlet().evaluate(0,0,5)
    0.5
    """
    def __init__(self, alpha=1., beta=1.):
        self.alpha = alpha
        self.alphabeta = alpha + beta

    def evaluate(self, count, success, length):
        return (self.alpha + success) / (self.alphabeta + count)

class ExponentialDirichlet(SmoothingStrategy):
    """
    The (symmetric) Dirichlet prior constants vary exponentially
    depending on the length
    """

    def __init__(self, k=1.5, a=8., b=0.1):
        self.k = k
        self.a = a
        self.b = b

    def evaluate(self, count, success, length):
        p = math.pow(self.k, (self.a - self.b*length))
        print('count: {}, success: {}, length: {}'.format(count, success, length))
        from urltheory.utils import min_count_for_confidence
        print('prior: {}, min_count at 0.8: {}'.format(p, min_count_for_confidence(0.8,(p,p))))
        return ConstantDirichlet(p,p).evaluate(count, success, length)

