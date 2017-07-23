# -*- encoding: utf-8 -*-

from gevent.lock import Semaphore
from urltheory.preftree import PrefTree
import pickle

class URLForest(object):
    """
    An URL forest is a set of URL trees (PrefTree) !
    Each tree is built for a specific classification task on URLs.
    For instance, a typical URL forest contains
    - a PrefTree to classify URLs leading to PDF, DjVu or PS files
    - a PrefTree to classify URLs of landing pages leading to full texts
    - a PrefTree to classify URLs that are registration-protected…

    This class is intended to be a greenlet-safe interface to these
    trees.
    """
    def __init__(self):
        self.trees = {}
        self.locks = {}

    def add_tree(self, id, tree=None):
        """
        Add a classifier tree for the 'id' class.
        If no tree is provided, we create a fresh one.
        Creates the associated lock.
        """
        if id in self.trees:
            raise ValueError(
                'A tree with id %s is already present.' % id)
        if tree is None:
            tree = PrefTree()
        self.trees[id] = tree
        self.locks[id] = Semaphore(1)

    def __contains__(self, key):
        return key in self.trees

    def match(self, id, *args, **kwargs):
        """
        Matches a URL with the tree identified by the identifier.
        All arguments after the first one are passed to PrefTree.match()
        """
        return self._run_method('match', id, *args, **kwargs)

    def match_length(self, id, *args, **kwargs):
        """
        Matches a URL with the tree identified by the identifier.
        All arguments after the first one are passed to PrefTree.match()
        """
        return self._run_method('match_length', id, *args, **kwargs)


    def add_url(self, id, *args, **kwargs):
        """
        Adds an URL to the tree identified by the identifier.
        All arguments after the first one are passed to PrefTree.add_url()
        """
        return self._run_method('add_url', id, *args, **kwargs)

    def print_as_tree(self, id, *args, **kwargs):
        return self._run_method('print_as_tree', id, *args, **kwargs)

    def _run_method(self, method, id, *args, **kwargs):
        """
        Internal wrapper that acquires the lock and runs a method of the
        tree.
        """
        if id not in self.trees:
            raise ValueError('Unknown id %s.' % id)
        self.locks[id].acquire()
        response = getattr(self.trees[id], method)(*args, **kwargs)
        self.locks[id].release()
        return response

    def clear(self):
        """
        Tears down the forest (please don't do this in Amazonia).
        """
        if any(s.locked() for s in list(self.locks.values())):
            raise ValueError('The forest is still in use.')
        self.trees.clear()
        self.locks.clear()

    def load(self, fname):
        """
        Loads the forest from a file (with pickle)
        """
        self.clear()
        with open(fname, 'rb') as f:
            new_trees = pickle.load(f)
            for id, tree in list(new_trees.items()):
                self.add_tree(id, tree)

    def save(self, fname):
        """
        Saves the forest to a file (with pickle)
        """
        with open(fname, 'wb') as f:
            pickle.dump(self.trees, f)

