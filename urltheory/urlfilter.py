# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict
from urltheory.preftree import *
from urltheory.tokenizer import *

import codecs, cPickle

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

    def load(self, fname):
        """
        Loads a corpus from a file.

        :param fname: filename of the TSV file to load
        """
        with open(fname, 'r') as f:
            for line in f:
                fields = line.strip().split('\t')
                if len(fields) != 2:
                    print "Invalid line, %d fields" % len(fields)
                    continue
                self.add_url(fields[0], fields[1] == '1')

    def train_filter(self, fltr):
        """
        Takes a (preconfigured) filter and feeds it with the 
        URLs stored in the corpus. The URLFilter is modified in place.

        :param fltr: a URLFilter
        """
        for url, success in self.urls:
            fltr.add_url(url, success)

    def cv_scores(self, fltr, folds=5):
        """
        Computes cross-validated scores of a filter.
        
        :param fltr: the URLFilter to train and score
        :param folds: the number of folds for cross-validation
        """
        batch_length = int(float(len(self.urls))/folds)
        confusion = {True:defaultdict(int),False:defaultdict(int)}
        for k in range(folds):
            test_set = []
            train_set = []
            for j in range(folds):
                cur_batch = self.urls[(k*batch_length):((k+1)*batch_length)]
                if j == k:
                    test_set = cur_batch
                else:
                    train_set += cur_batch
            
            fltr.clear()
            for url, success in train_set:
                fltr.add_url(url, success)
            fltr.force_prune()

            for url, refsuccess in test_set:
                predsuccess = fltr.predict_success(url)
                confusion[refsuccess][predsuccess] += 1

        return confusion


class URLFilter(object):
    """
    Classifies URLs using a PrefTree that is regularly pruned.
    """
    def __init__(self, prune_delay=20,
            reverse=True,
            min_urls_prune=10,
            min_children=2,
            min_rate=0.9,
            threshold=0.9):
        """
        :param prune_delay: the number of added urls between each prune
        """
        self.prune_delay = prune_delay
        self.reverse = reverse
        self.min_urls_prune = min_urls_prune
        self.min_children = min_children
        self.min_rate = min_rate
        self.threshold = threshold

        self.last_prune = 0
        self.t = PrefTree()

    def _prune_kwargs(self):
        """
        Returns the prune keyword arguments to be passed to
        PrefTree.prune
        """
        return {'reverse':self.reverse,
                'min_urls':self.min_urls_prune,
                'min_children':self.min_children,
                'min_rate':self.min_rate}
    

    def add_url(self, url, success=False, keep_pruned=True):
        """
        :param url: the URL to add to the filter
        :param success: whether we should consider it successful
        """
        tokenized = prepare_url(url)
        if not tokenized:
            return
        
        if keep_pruned:
            self.t.add_url(tokenized, success=success, prune_kwargs=self._prune_kwargs())
        else:
            self.t.add_url(tokenized, success=success)
            self.last_prune += 1
            if self.prune_delay and self.last_prune >= self.prune_delay:
                self.force_prune()

    def force_prune(self):
        """
        Prunes the tree according to the parameters stored in the filter.
        """
        self.t, pruned = self.t.prune(**self._prune_kwargs())
        self.last_prune = 0

    def predict_success(self, url):
        """
        Predicts the success of a given URL with the prefix tree
        """
        tokenized = prepare_url(url)
        return self.t.predict_success(tokenized, confidence_threshold=self.threshold)

    def clear(self):
        """
        Clears the underlying PrefTree (removes all URLs and patterns it contains)
        """
        del self.t
        self.t = PrefTree()

    def load(self, fname):
        """
        Loads the URL filter from a file
        """
        with open(fname, 'rb') as f:
            dct = cPickle.load(f)
            self.__dict__.update(dct)

    def save(self, fname):
        """
        Saves the URL filter to a file
        """
        with open(fname, 'wb') as f:
            cPickle.dump(self.__dict__, f) 

