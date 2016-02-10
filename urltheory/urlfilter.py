# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from urltheory.preftree import *
from urltheory.tokenizer import *

import codecs

class URLCorpus(object):
    """
    Stores a set of URLs and uses it to train an :class:`URLFilter`
    """
    def __init__(self):
        self.out_sync = None
        self.urls = []

    def write_to_file(self, fname, keep_in_sync=False):
        """
        Writes the content of the URLCorpus to a file in tsv format
        """
        f = codecs.open(fname, 'w', 'utf-8')
        for item in self.urls:
            self._write_url(item, f)
        if not keep_in_sync:
            f.close()
        else:
            self.out_sync = f

    def _write_url(self, (url,success), f):
        f.write('\t'.join([url, ('1' if success else '0')])+'\n')

    def add_url(self, url, success=False):
        """
        Adds an URL to the corpus
        """
        if self.out_sync is not None:
            self._write_url((url,success), self.out_sync)
        self.urls.append((url,success))

    def predict_success(self, url):
        """
        Provided for convenience (so that an URLCorpus behaves like a trivial URLFilter)
        """
        return None
        

class URLFilter(object):
    """
    Classifies URLs using a PrefTree that is regularly pruned.
    """
    def __init__(self, prune_delay=20,
            reverse=True,
            min_urls_prune=10,
            min_children=2,
            min_rate=0.9,
            threshold=0.9,
            min_urls_prediction=10):
        """
        :param prune_delay: the number of added urls between each prune
        """
        self.prune_delay = prune_delay
        self.reverse = reverse
        self.min_urls_prune = min_urls_prune
        self.min_children = min_children
        self.min_rate = min_rate
        self.threshold = threshold
        self.min_urls_prediction = min_urls_prediction

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
        self.t, pruned = self.t.prune(reverse=self.reverse,
                min_urls=self.min_urls_prune,
                min_children=self.min_children,
                min_rate=self.min_rate)
        self.last_prune = 0
        self.t.print_as_tree()

    def predict_success(self, url):
        """
        Predicts the success of a given URL with the prefix tree
        """
        tokenized = prepare_url(url)
        return self.t.predict_success(tokenized, threshold=self.threshold,
                min_urls=self.min_urls_prediction)

