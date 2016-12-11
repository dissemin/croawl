# -*- encoding: utf-8 -*-
from __future__ import unicode_literals


class AccessPredict(object):
    """
    Predicts the access level for a particular URL.
    """
    def __init__(self, predictors=[]):
        self.predictors = predictors

    def predict_url(self, url):
        for p in self.predictors:
            answer = p.filtered_predict(url)
            if answer:
                return answer

