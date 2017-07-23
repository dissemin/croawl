# -*- encoding: utf-8 -*-


import requests
from gevent import monkey
monkey.patch_all(thread=False, select=False)

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

