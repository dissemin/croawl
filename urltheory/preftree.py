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

    def __init__(self):
        """
        Creates a leaf, with success set to false.
        """
        self.children = {}
        self.url_count = 0
        self.success_count = 0
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

        leaf_node = PrefTree()
        leaf_node.url_count = 1
        self.url_count += 1
        if success:
            leaf_node.success_count = 1
            self.success_count += 1

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


