# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
from .predictor import URLCategoryPredictor

class CombinedPredictor(URLCategoryPredictor):
    """
    Boolean combination of predictors
    """
    def predict_before_fetch(self, url, tokenized_url,
                min_confidence=0.8):
        return self._val(url, min_confidence)

    def _val(self, url, min_confidence):
        """
        This is the method where the boolean combination should be
        computed
        """
        raise NotImplemented()

    def __eq__(self, other):
        return EqualCombinedPredictor(self, other)
    def __ne__(self, other):
        return NotEqualCombinedPredictor(self, other)
    def __or__(self, other):
        return OrCombinedPredictor(self, other)
    def __and__(self, other):
        return AndCombinedPredictor(self, other)

    def __repr__(self):
        return '<%s>' % self.__unicode__()

class P(CombinedPredictor):
    """
    A predictor that replicates another or negates it.
    Syntax:
    P('pdf') replicates the 'pdf' class_id
    P('not pdf') negates it
    """
    def __init__(self, class_id, **kwargs):
        super(P, self).__init__(**kwargs)
        if class_id.startswith('not '):
            self.class_id = class_id[4:]
            self.negated = True
        else:
            self.class_id = class_id
            self.negated = False

    def _val(self, url, min_confidence):
        upstream_proba = self.spider.predict(self.class_id, url, min_confidence)
        return 1. - upstream_proba if self.negated else upstream_proba

    def __unicode__(self):
        return 'P(%s)' % self.class_id

class BinaryCombinedPredictor(CombinedPredictor):
    operator = None

    def __init__(self, p1, p2, **kwargs):
        self.p1 = p1
        self.p2 = p2
        super(BinaryCombinedPredictor, self).__init__(**kwargs)

    def set_spider(self, spider):
        self.p1.set_spider(spider)
        self.p2.set_spider(spider)

    def _val(self, url, min_confidence):
        """
        Combines the probabilities output by p1 and p2
        into the proba of the compound, by calling
        p1 and p2 with the appropriate min_confidence
        """
        upstream_min_conf = self.upstream_min_confidence(self, min_confidence)
        x1 = self.p1._val(url, upstream_min_conf)
        x2 = self.p2._val(url, upstream_min_conf)
        return self.combine_probas(x1, x2)

    def upstream_min_confidence(self, min_confidence):
        """
        To be reimplemented: computes the confidence with which
        child classifiers should be called.
        """
        raise NotImplemented()

    def combine_probas(self, x1, x2):
        """
        To be reimplemented: combines the outputs of the
        two children.
        """
        raise NotImplemented()

    def __unicode__(self):
        return ' '.join([unicode(self.p1), self.operator, unicode(self.p2)])

class EqualCombinedPredictor(BinaryCombinedPredictor):
    operator = '=='
    def combine_probas(self, x1, x2):
        return x1*x2 + (1 - x1)*(1 - x2)
    def upstream_min_confidence(self, c):
        return (1. + sqrt(1. - 2.*(1.-c)))/2.

class NotEqualCombinedPredictor(BinaryCombinedPredictor):
    operator = '!='
    def combine_probas(self, x1, x2):
        return x1*(1 - x2) + (1 - x1)*x2
    def upstream_min_confidence(self, c):
        return (1. + sqrt(1. - 2.*(1.-c)))/2

class AndCombinedPredictor(BinaryCombinedPredictor):
    operator = '&'
    def combine_probas(self, x1, x2):
        return x1*x2
    def upstream_min_confidence(self, c):
        return sqrt(c)

class OrCombinedPredictor(BinaryCombinedPredictor):
    operator = '|'
    def combine_probas(self, x1, x2):
        return x1 + x2 - x1*x2
    def upstream_min_confidence(self, c):
        return sqrt(c)

