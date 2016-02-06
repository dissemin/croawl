# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import hashable_collections.hashable_collections as hashable

from urltheory.utils import *

class PrefTree(object):
    """
    A prefix tree, storing a collection of strings
    and 'generalizing' them using their prefixes.
    This is designed to work with URLs, so in the following
    strings are called URLs.

    A tree is either:
    - a leaf, in which case it contains a `success`
      boolean indicating whether the URL leading to that
      leaf contained the information we are looking for.
    - an internal node, in which case it contains a dictionary
      of `children`, whose keys are the parts of URLs one has
      to append to the current node to get to each child.
    - a wildcard, understood as something that matches any string.

    Each tree also stores two integers, indicating:
    - `url_count`, the number of URLs it was generated from (one
      for each leaf, and an arbitrary number for each wildcard)
    - `success_count`, the number of successes among these urls,
      which has to be less

    The keys of children in internal nodes are required not
    to share any common prefix (if so, we need to refactor them
    by adding an intermediate internal node) and to be non-null.
    """

    def __init__(self, url_count=0, success_count=0, success=None):
        """
        Creates a leaf.

        :param url_count: the number of urls leading to that leaf
        :param success_count: the number of successful urls leading to that leaf
        :param success: if True, sets both url_count and success_count to 1
        """
        self.children = {}
        if success is True:
            success_count = 1
            url_count = 1
        elif success is False:
            success_count = 0
            url_count = 1
        self.url_count = url_count
        self.success_count = success_count
        self.is_wildcard = False

    def __getitem__(self, key):
        """
        Shorthand for `children[key]`
        """
        if isinstance(key, hashable.hashable_list):
            return self.children[key]
        else:
            return self.children[hashable.hashable_list(key)]

    def __setitem__(self, key, value):
        """
        Shorthand for `children[key] = value`
        """
        if isinstance(key, hashable.hashable_list):
            self.children[key] = value
        else:
            self.children[hashable.hashable_list(key)] = value

    def __delitem__(self, key):
        """
        Shorthand for `del children[key]`.
        """
        if isinstance(key, hashable.hashable_list):
            del self.children[key]
        else:
            del self.children[hashable.hashable_list(key)]

    def add_url(self, url, success):
        """
        Recursively adds an URL to the prefix tree
        """
        found = False

        leaf_node = PrefTree(success=success)
        self.url_count += leaf_node.url_count
        self.success_count += leaf_node.success_count

        if self.is_wildcard:
            # a wildcard already matches the url to be added
            return

        for key in self.children:
            lcp = longest_common_prefix(url, key)
            if len(lcp) == 0:
                continue
            if len(lcp) < len(key):
                # We need to create an intermediate internal node
                new_node = PrefTree()
                old_node = self[key]
                new_node[key[len(lcp):]] = old_node

                new_node[url[len(lcp):]] = leaf_node 

                new_node.url_count = old_node.url_count + leaf_node.url_count
                new_node.success_count = old_node.success_count + leaf_node.success_count
                del self[key]
                self[lcp] = new_node
            else: # len(lcp) == len(key)
                # Recursively add the url to the next internal node
                self.children[key].add_url(url[len(lcp):], success)
            found = True
            break
        
        if not found and len(url) > 0 and not self.is_wildcard:
            # if no internal node with a matching prefix was found
            # then add a new one with that prefix
            self[url] = leaf_node

    def match(self, url):
        """
        Returns the number of time this URL was added and the number of time
        it was a success.
        """
        if self.is_wildcard:
            return (self.url_count, self.success_count)

        # ensure we are dealing with a non-flattened list (not a string)
        if type(url) != list:
            url = [c for c in url]

        urls = 0
        successes = 0
        for path in self.children:
            subtree = self[path]
            urls += subtree.url_count
            successes += subtree.success_count
            if list(url[:len(path)]) == list(path):
                return subtree.match(url[len(path):])
        if len(url) == 0:
            return (self.url_count - urls, self.success_count - successes)
        return (0,0)

    def prune(self, min_urls=1, min_children=2, min_rate=1.):
        """
        Replaces subtrees where the rate of success is above min_rate
        or below (1 - min_rate) by a wildcard, with the same url and success
        counts.

        :param min_urls: only prune subtrees that have at least `min_urls` urls.
            This parameter has to be positive.
        :param min_children: only prune subtrees that have at least that
            many children.
        """
        if min_urls <= 0:
            raise ValueError('Invalid min_urls parameter in PrefTree.prune')

        if (self.url_count >= min_urls and
            len(self.children) >= min_children and
            float(self.success_count)/self.url_count >= min_rate):
            self.is_wildcard = True
            self.children.clear()
        
        for path in self.children:
            self.children[path].prune(min_urls=min_urls,
                                    min_children=min_children,
                                    min_rate=min_rate)


    def urls(self, prepend=[]):
        """
        Prints the list of URLs contained in the prefix tree

        :param prepend: first part of the URL, to be prepended to all URLs
        """
        if len(self.children) == 0:
            if self.is_wildcard:
                return [prepend + ['*']]
            return [prepend]
        else:
            res = []
            for key in self.children:
                new_prepend = prepend + key
                res += self[key].urls(new_prepend)
            return res

    def print_as_tree(self, level=0, last_label='ROOT'):
        """
        Prints the tree as it is stored
        """
        pipes = ''
        if level > 0:
            pipes = ((level-1)*'| ')+'|-'

        if len(self.children) == 0:
            if self.is_wildcard:
                last_label += '*'
        print pipes+last_label+(' (%d/%d)'%(self.success_count,self.url_count))
        for key, val in self.children.items():
            val.print_as_tree(level+1, last_label=flatten(key))

    def check_sanity(self, nonempty=False):
        """
        Recursively check that the tree is valid.

        :param nonempty: set to `True` to ensure that the tree contains
            at least one URL

        :returns: True if the tree is valid
        """
        # 1 / Check that no children share a common prefix
        keys = list(self.children.keys())
        for i in range(len(keys)):
            for j in range(i):
                if longest_common_prefix(keys[i],keys[j]):
                    return False

        # 2 / Check that the number of urls and successes are consistent
        num_url_children = sum([c.url_count for c in self.children.values()])
        num_success_children = sum([c.success_count for c in self.children.values()])
        num_leaf_urls = self.url_count - num_url_children
        num_leaf_successes = self.success_count - num_success_children
        if not (num_leaf_urls >= 0 and 
                num_leaf_successes >= 0 and
                num_leaf_successes <= num_leaf_urls and
                (not nonempty or self.url_count > 0)):
            return False
        
        # 3 / A wildcard has no children
        if self.is_wildcard and len(keys):
            return False

        # 4 / Recursively check the children
        for val in self.children.values():
            if not val.check_sanity(True):
                return False

        return True

