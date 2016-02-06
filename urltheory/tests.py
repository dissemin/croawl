# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import doctest
from hashable_collections.hashable_collections import hashable_list

import urltheory
import urltheory.tokenizer
from urltheory.preftree import PrefTree
from urltheory.utils import flatten

class PrefTreeTest(unittest.TestCase):
    def test_empty(self):
        t = PrefTree()
        self.assertTrue(t.check_sanity())

    def test_create(self):
        t = PrefTree()
        urls = ['aaba','cadb','abdc','abcd','afgh','abec']
        for u in urls:
            t.add_url(u, False)
            self.assertTrue(t.check_sanity())
        t.print_as_tree()

        self.assertEqual(sorted(map(flatten, t.urls())), sorted(urls))
        for u in urls:
            self.assertEqual(t.match(u), (1,0))
        self.assertEqual(t.match('bac'), (0,0))

    def test_wildcard(self):
        t = PrefTree()
        t.add_url('arxiv.org/pdf/', True)
        t['arxiv.org/pdf/'].is_wildcard = True
        self.assertTrue(t.check_sanity())
        self.assertEqual(t.match('arxiv.org/pdf/1410.1454v2'), (1,1))
        t.add_url('arxiv.org/pdf/1412.8548v1', True)
        self.assertEqual(t.match('arxiv.org/pdf/1410.1454v2'), (2,2))
        t.print_as_tree()
        self.assertEqual(len(t.urls()), 1)

    def test_prune(self):
        t = PrefTree()
        with self.assertRaises(ValueError):
            t.prune(min_urls=0)

        for url, success in [
                ('arxiv.org/pdf/1410.1234', True),
                ('arxiv.org/pdf/1409.1094', True),
                ('arxiv.org/pdf/1201.5480', True),
                ('arxiv.org/pdf/1601.01234', True),
                ('arxiv.org/pdf/1602.01i34', False), # oops
                ]:
            t.add_url(url, success)
        t.prune(min_rate=0.75,min_children=2,min_urls=1)
        self.assertEqual(len(t.urls()), 1)
        self.assertEqual(t.match('arxiv.org/pdf/1784.1920'), (5,4))
        self.assertEqual(t.match('arxiv.org/pdf/2340.0124'), (0,0))
        t.print_as_tree()

    def test_accessors(self):
        t = PrefTree()
        urls = ['arxiv.org/abs/1410.1454','arxiv.org/pdf/1410.1454v2']
        for u in urls:
            t.add_url(u, True)
        self.assertEqual(t['arxiv.org/'], t[hashable_list('arxiv.org/')])
        t['biorxiv.org/'] = PrefTree()
        t[hashable_list('sciencedirect.com/')] = PrefTree()
        del t[hashable_list('biorxiv.org/')]
        del t['sciencedirect.com/']

    def test_check_sanity(self):
        t = PrefTree()
        t['abc'] = PrefTree()
        t['aa'] = PrefTree()
        self.assertFalse(t.check_sanity())

        t = PrefTree(url_count=-1)
        self.assertFalse(t.check_sanity())

        t = PrefTree()
        t['abc'] = PrefTree()
        t.is_wildcard = True
        self.assertFalse(t.check_sanity())

        t2 = PrefTree()
        t2['def'] = t
        self.assertFalse(t2.check_sanity())


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(urltheory.tokenizer))
    tests.addTests(doctest.DocTestSuite(urltheory.utils))
    return tests

