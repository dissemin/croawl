# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import doctest

import urltheory
from urltheory.preftree import PrefTree

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

        self.assertEqual(sorted(map(flatten, t.urls())), sorted(urls))

def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(urltheory.utils))

