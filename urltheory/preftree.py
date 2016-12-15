# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import hashable_collections.hashable_collections as hashable

from urltheory import utils
from urltheory.tokenizer import flatten_to_re

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

    def assign(self, other):
        """
        Copies other into self.
        """
        self.__dict__ = other.__dict__.copy()
        self.__class__ = other.__class__

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

    @property
    def confidence(self):
        return utils.confidence(self.url_count, self.success_count)

    def add_url(self, url, success=None, url_count=1, success_count=0, prune_kwargs=None):
        """
        Recursively adds an URL to the prefix tree.
        Adding an URL with a WilcardCharacter forces the addition of a wildcard in
        the tree at the designated position.

        :param success: boolean: if set to True, url_count, success_count = 1, 1
                        if set to False, url_count, success_count = 1, 0
        :param url_count: custom number of urls matching this pattern
        :param success_count: custom number of successful urls matching this pattern
        :param prune_kwargs: should we simultaneously keep the tree pruned? if so,
            this parameter should contain the dict of parameters used by prune()
            (passed as **kwargs).
        """
        found = False

        leaf_node = PrefTree(success=success, url_count=url_count,
                success_count=success_count)
        self.url_count += leaf_node.url_count
        self.success_count += leaf_node.success_count

        if self.is_wildcard:
            # a wildcard already matches the url to be added
            return

        for key in self.children:
            lcp = utils.longest_common_prefix(url, key)
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
            else: # in this case, len(lcp) == len(key)
                # Recursively add the url to the next internal node
                self.children[key].add_url(url[len(lcp):], success=success,
                        url_count=url_count, success_count=success_count,
                        prune_kwargs=prune_kwargs)
            found = True
            break

        if not found and len(url) > 0 and not self.is_wildcard:
            found = True
            # if the url we are trying to add starts with a wildcard
            if url[0] == utils.WildcardCharacter():
                # then just convert the tree to a wildcard
                self.is_wildcard = True
                self.children.clear()
            else:
                # if no internal node with a matching prefix was found
                # then add a new one with that prefix
                self[url] = leaf_node

        if found and prune_kwargs is not None:
            # We have added a node to our tree, so we should try to prune (non-recursively)
            kwargs = prune_kwargs.copy()
            kwargs['recurse'] = False
            pruned, success = self.prune(**kwargs)
            if success:
                self.assign(pruned)

    def match(self, url, confidence_threshold=None):
        """
        Returns the number of times this URL was added and the number of times
        it was marked as a success.

        :returns: a pair of integers
        """
        tot_count, success_count, _ = self.match_with_branch(url,
                                confidence_threshold=confidence_threshold)
        return (tot_count, success_count)

    def match_with_branch(self, url, confidence_threshold=None):
        """
        As match(), returns the total and success count for a given URL,
        but also the pattern of the branch corresponding to that URL in the tree.

        :para url: the tokenized url to match
        :para confidence_threshold: a float (if provided). if the
                classification confidence is above that threshold,
                stop matching and return the majority vote

        :returns: a tuple: (total_count, success_count, branch)
            where the branch is a list listing all the labels of the branches.
        """
        if self.is_wildcard:
            return (self.url_count, self.success_count, ['*'])

        # ensure we are dealing with a non-flattened list (not a string)
        if type(url) != list:
            url = [c for c in url]

        if confidence_threshold:
            current_confidence = utils.confidence(self.url_count,
                    self.success_count)
            if current_confidence > confidence_threshold:
                return (self.url_count, self.success_count, ['<early>'])

        urls = 0
        successes = 0
        for path in self.children:
            subtree = self[path]
            urls += subtree.url_count
            successes += subtree.success_count
            if list(url[:len(path)]) == list(path):
                tot_count, suc_count, sub_branch = subtree.match_with_branch(
                        url[len(path):],
                        confidence_threshold=confidence_threshold)
                return (tot_count, suc_count, path + sub_branch)

        if len(url) == 0:
            return (self.url_count - urls, self.success_count - successes, [])
        return (0,0, ['<unk>'])

    def print_subtree(self, url):
        """
        Print the subtree rooted at the given branch
        """
        # ensure we are dealing with a non-flattened list (not a string)
        if type(url) != list:
            url = [c for c in url]

        if url == []:
            self.print_as_tree()
            return

        for path in self.children:
            if list(url[:len(path)]) == list(path):
                self[path].print_subtree(url[len(path):])
                return

        print "unmatched: "
        print url
        self.print_as_tree()


    def predict_success(self, url, confidence_threshold=0.95):
        """
        Returns True when the number of successes matching this url
        is positive and above threshold * url_count, which corresponds
        to predicting a success.
        Returns False when it predicts a failure, and returns nothing
        when it fails to predict.
        """
        url_count, success_count = self.match(url, confidence_threshold)
        c = utils.confidence(url_count, success_count)
        if c > confidence_threshold:
            return 2*success_count >= url_count

    def prune(self, confidence_threshold=1.0, reverse=False, recurse=True):
        """
        Replaces subtrees where the confidence is higher than the
        threshold by a wildcard, with the same url and success counts.

        The function returns a new version of the tree, but the original tree
        might also have been modified.

        :param confidence_threshold: the confidence above which we should
            replace subtrees by a wildcard
        :param reverse: try to reverse subtrees when they are good candidates
            for a prune.
        :param recurse: prune the tree recursively
        :returns: a pair: the value of the new pruned tree,
            and a boolean indicating whether some part of the tree has been pruned
        """
        if confidence_threshold <= 0:
            raise ValueError('The confidence threshold has to be positive.')
        if self.url_count == 0:
            return (self, False)

        # Is this a good candidate for a prune ?
        should_be_pruned = (self.confidence >= confidence_threshold and
                            len(self.children) > 0)
        has_been_pruned = False

        success_rate = float(self.success_count)/self.url_count
        if should_be_pruned:
            self.is_wildcard = True
            self.children.clear()
            has_been_pruned = True

        if recurse:
            for path in self.children:
                new_child, child_pruned = self.children[path].prune(
                                        confidence_threshold=confidence_threshold,
                                        reverse=reverse,
                                        recurse=True)
                if child_pruned:
                    self[path] = new_child
                    has_been_pruned = True

        # If it is a good candidate for a prune, but has not been pruned,
        # we can try reversing the urls
        if (reverse and not has_been_pruned):
            urls = self.urls()
            rev = RevPrefTree()
            for u, match_count, success_count in urls:
                rev.add_url(u, url_count=match_count, success_count=success_count)

            rev, pruned = rev.prune(confidence_threshold=confidence_threshold,
                     reverse=False, recurse=True)
            if pruned:
                return (rev, True)

        return (self, has_been_pruned)

    def urls(self, prepend=[]):
        """
        Prints the list of URLs contained in the prefix tree

        :param prepend: first part of the URL, to be prepended to all URLs
        :returns: a list of tuples: (url, matches_count, success_count)
        """
        if len(self.children) == 0:
            if self.is_wildcard:
                return [(prepend + [utils.WildcardCharacter()],self.url_count,self.success_count)]
            return [(prepend,self.url_count,self.success_count)]
        else:
            res = []
            total_url_count = 0
            total_success_count = 0
            for key in self.children:
                new_prepend = prepend + key
                child_urls = self[key].urls(new_prepend)
                res += child_urls
                total_url_count += sum([c for u, c, s in child_urls])
                total_success_count += sum([s for u, c, s in child_urls])

            if total_url_count < self.url_count:
                res.append((prepend, (self.url_count - total_url_count),
                              (self.success_count - total_success_count)))
            return res

    def has_wildcard(self):
        """
        Returns True when there is at least one wildcard in this tree.
        """
        if self.is_wildcard:
            return True
        for subtree in self.children.values():
            if subtree.has_wildcard():
                return True
        return False

    def print_as_tree(self, levels=[], last_label='ROOT', is_last_child=True):
        """
        Prints the tree as it is stored
        """
        pipes = (''.join(levels) + ('└─' if is_last_child else '├─'))
        children_levels = levels + ['  ' if is_last_child else '│ ']

        if len(self.children) == 0:
            if self.is_wildcard:
                last_label += '*'

        # compute the color of the label
        color = '\033[30;1m%s\033[0m'
        if self.url_count:
            rate = float(self.success_count) / self.url_count
            if rate > 0.9:
                color = '\033[32;7m%s\033[0m'
            elif rate > 0.1:
                color = '\033[33;7m%s\033[0m'
        count_label = color % ('(%d/%d)' %
                    (self.success_count, self.url_count))
        if type(last_label) == str:
            last_label = last_label.decode('utf-8')

        print (pipes+last_label+(' '+count_label)).encode('utf-8')

        nb_children = len(self.children)
        for i, (key, val) in enumerate(self.children.items()):
            val.print_as_tree(children_levels,
                             last_label=utils.flatten(key),
                              is_last_child=(i==nb_children-1))

    def _generate_regex_internal(self, confidence_threshold=0.9,
                            reverse=False):
        """
        Internal function regex generation
        """
        if len(self.children) == 0:
            if (2*self.success_count < self.url_count or
                self.confidence < confidence_threshold):
                return ''
            else:
                return '.*' if self.is_wildcard else ''

        children_regexes = [
            child.generate_regex(confidence_threshold, branch, reverse)
            for branch, child in self.children.items()
        ]
        filtered_children = filter(lambda u: bool(u),
                                    children_regexes)

        children_disjunct = str('|').join(filtered_children)
        if len(filtered_children) > 1:
            children_disjunct = str('(%s)') % children_disjunct
        return children_disjunct

    def generate_regex(self, confidence_threshold=0.9,
                            leading_branch=[],
                            reverse=False):
        """
        Creates a regular expression that matches strings which
        match successful branches of the tree, with a confidence
        higher than the threshold.

        This regular expression should then be completed
        with "^" and "$" markers.

        The regular expression matching only the empty string
        is treated as matching the empty language.
        """
        internal_re = self._generate_regex_internal(
                confidence_threshold, reverse)
        if not internal_re:
            return ''

        leading_re = flatten_to_re(leading_branch, reverse=reverse)
        if reverse:
            return internal_re + leading_re
        else:
            return leading_re + internal_re

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
                if utils.longest_common_prefix(keys[i],keys[j]):
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

class RevPrefTree(PrefTree):
    """
    A reversed prefix tree (aka postfix tree).
    All urls sent to it are reversed.
    See :class:`PrefTree` for the documentation.
    """
    def add_url(self, url, success=None, **kwargs):
        """
        Recursively adds an URL to the postfix tree
        """
        super(RevPrefTree, self).add_url(list(reversed(url)), success=success, **kwargs)

    def match_with_branch(self, url, **kwargs):
        """
        Returns the number of time this URL was added and the number of time
        it was a success, and the branch of that URL in the tree.
        """
        tot, suc, branch = super(RevPrefTree,
                    self).match_with_branch(list(reversed(url)), **kwargs)
        return tot, suc, list(reversed(branch))

    def urls(self, prepend=[]):
        """
        Prints the list of URLs contained in the prefix tree

        :param prepend: first part of the URL, to be prepended to all URLs
        """
        reversed_urls = [(list(reversed(l)), u, s) for l, u, s in
                super(RevPrefTree, self).urls()]
        return [(prepend+url,c,s) for url, c, s in reversed_urls]

    def print_as_tree(self, levels=[], last_label='ROOT', is_last_child=True):
        """
        Prints the postfix tree as a prefix tree, adding warnings
        to show that it is in fact a postfix tree
        """
        last_label = '\033[31;7mreversed\033[0m %s' % last_label
        super(RevPrefTree, self).print_as_tree(levels, last_label, is_last_child)

    def generate_regex(self, confidence_threshold=0.9,
                            leading_branch=[],
                            reverse=False):
        """
        Creates a regular expression that matches strings which
        match successful branches of the tree, with a confidence
        higher than the threshold.

        This regular expression should then be completed
        with "^" and "$" markers.

        The regular expression matching only the empty string
        is treated as matching the empty language.
        """
        internal_re = self._generate_regex_internal(
                confidence_threshold, not reverse)
        if not internal_re:
            return ''

        leading_re = flatten_to_re(leading_branch, reverse=reverse)
        if reverse:
            return internal_re + leading_re
        else:
            return leading_re + internal_re
