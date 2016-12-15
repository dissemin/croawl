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


