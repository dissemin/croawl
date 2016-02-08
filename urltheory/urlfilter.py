# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from urltheory.preftree import *
from urltheory.tokenizer import *

class URLFilter(object):
    """
    Classifies URLs using a PrefTree that is regularly pruned.
    """
    def __init__(self, prune_delay=20,
            reverse=True,
            min_urls=10,
            min_children=2,
            min_rate=0.9,
            threshold=0.9):
        """
        :param prune_delay: the number of added urls between each prune
        """
        self.prune_delay = prune_delay
        self.reverse = reverse
        self.min_urls = min_urls
        self.min_children = min_children
        self.min_rate = min_rate
        self.threshold = threshold

        self.last_prune = 0
        self.t = PrefTree()

    def add_url(self, url, success=False):
        """
        :param url: the URL to add to the filter
        :param success: whether we should consider it successful
        """
        tokenized = prepare_url(url)
        if not tokenized:
            return
        self.t.add_url(tokenized, success=success)
        self.last_prune += 1
        if self.last_prune >= self.prune_delay:
            self.force_prune()

    def force_prune(self):
        """
        Prunes the tree according to the parameters stored in the filter.
        """
        self.t.prune(reverse=self.reverse,
                min_urls=self.min_urls,
                min_children=self.min_children,
                min_rate=self.min_rate)
        self.last_prune = 0

    def predict_success(self, url):
        """
        Predicts the success of a given URL with the prefix tree
        """
        tokenized = prepare_url(url)
        return self.t.predict_success(tokenized, threshold=self.threshold)

