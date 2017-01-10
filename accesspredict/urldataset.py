# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
from datetime import date
from datetime import timedelta
from urltheory.tokenizer import normalize_url
from urltheory.tokenizer import prepare_url

class URLDataset(object):
    """
    A redis-stored database of URLs
    """

    def __init__(self, redis_client):
        self.client = redis_client

    def get(self, url, class_id):
        """
        Have we ever classified this URL?
        If yes, returns a dict with the value
        and the date it was set.
        Otherwise None.
        """
        url = normalize_url(url)
        val = self.client.hget(class_id, url)
        if not val:
            return
        fields = val.split(':')
        return (float(fields[0]), fields[1])

    def get_if_recent(self, url, class_id, ttl=timedelta(days=6*30)):
        """
        Same as get, but only returns only the boolean value,
        and only when the timestamp is fresh enough.
        """
        v = self.get(url, class_id)
        if v is None:
            return None
        val, datestamp = v
        d = date(year=int(datestamp[:4]),
                month=int(datestamp[5:7]),
                day=int(datestamp[8:10]))
        if d+ttl >= date.today():
            return val

    def set(self, url, class_id, value, datestring=None):
        """
        Stores the value of the classification for a particular URL
        If a date string is not provided, it will be set to today.
        """
        url = normalize_url(url)
        val = '%f:%s' % (
                 value,
                 datestring or date.today().isoformat())
        self.client.hset(class_id, url, val)

    def load(self, fname):
        """
        Loads the dataset from a text file
        """
        with open(fname, 'r') as f:
            for line in f:
                fields = line.strip().split('\t')
                day = fields[0]
                class_id = fields[1]
                value = float(fields[2])
                url = fields[3]
                self.set(url, class_id, value, day)

    def feed_to_tree(self, class_id, tree):
        """
        Adds all the URLs in the dataset to a given tree
        """
        for url, val, datestamp in self._iterate_urls(class_id):
            tree.add_url(prepare_url(url), val)
        return tree

    def feed_to_forest(self, forest):
        """
        Dumps the dataset into an URLForest.
        This bypasses the locks in the URLForest as it
        isn't designed for concurrent usage.
        """
        for class_id in self._iterate_classes():
            new_tree = self.feed_to_tree(class_id, forest.trees[class_id])
            forest.trees[class_id] = new_tree

    def _iterate_urls(self, class_id):
        """
        Iterates over the contents of a class
        """
        for item in self.client.hscan_iter(class_id):
            url, redis_val = item
            parsed = redis_val.split(':')
            val = float(parsed[0])
            datestamp = parsed[1]
            yield (url, val, datestamp)

    def _iterate_classes(self):
        """
        Iterates over the classes in this dataset
        """
        return self.client.scan_iter()

    def save(self, fname):
        """
        Saves the dataset to a file
        """
        with open(fname, 'w') as f:
            for class_id in self._iterate_classes():
                for (url, val, datestamp) in self._iterate_urls(class_id):
                    val = str(val)
                    f.write(str('\t').join([datestamp, class_id, val, url])+str('\n'))

