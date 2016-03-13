# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import doctest
from hashable_collections.hashable_collections import hashable_list

import urltheory
from urltheory.tokenizer import *
from urltheory.preftree import PrefTree, RevPrefTree
from urltheory.urlfilter import *
from urltheory.utils import flatten

class PrefTreeTest(unittest.TestCase):
    def test_empty(self):
        t = PrefTree()
        self.assertTrue(t.check_sanity())

    def test_create(self):
        t = PrefTree()
        urls = ['aaba','cadb','abdc','abcd','afgh','abec']
        for u in urls:
            t.add_url(u)
            self.assertTrue(t.check_sanity())
        self.assertFalse(t.has_wildcard())
        t.print_as_tree()

        self.assertEqual(sorted([flatten(u) for u, c, s in t.urls()]), sorted(urls))
        for u in urls:
            self.assertEqual(t.match(u), (1,0))
        self.assertEqual(t.match('bac'), (0,0))

    def test_urls(self):
        t = PrefTree()
        urls = ['aa','aa.pdf','bb','bb.pdf']
        for u in urls:
            t.add_url(u)
        self.assertEqual(len(t.urls()), 4)

    def test_wildcard(self):
        t = PrefTree()
        t.add_url('arxiv.org/pdf/', True)
        t['arxiv.org/pdf/'].is_wildcard = True
        self.assertTrue(t.check_sanity())
        self.assertTrue(t.has_wildcard())
        self.assertEqual(t.match('arxiv.org/pdf/1410.1454v2'), (1,1))
        t.add_url('arxiv.org/pdf/1412.8548v1', True)
        self.assertEqual(t.match('arxiv.org/pdf/1410.1454v2'), (2,2))
        t.print_as_tree()
        self.assertEqual(len(t.urls()), 1)

    def test_with_tokenization(self):
        t = PrefTree()
        t.add_url(prepare_url('eprint.iacr.org/2016/093'), False)
        t.add_url(prepare_url('eprint.iacr.org/2016/093.pdf'), True)
        t.add_url(prepare_url('eprint.iacr.org/2015/1248.pdf'), True)
        t.add_url(prepare_url('eprint.iacr.org/2015/1248'), False)
        t.print_as_tree()
        self.assertEqual(t.match(prepare_url('eprint.iacr.org/2014/528.pdf')), (2,2))
        self.assertEqual(t.match(prepare_url('eprint.iacr.org/2014/528')), (2,0))

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
        t, pruned = t.prune(min_rate=0.75,min_children=2,min_urls=1)
        self.assertEqual(len(t.urls()), 1)
        self.assertTrue(t.has_wildcard())
        self.assertEqual(t.match('arxiv.org/pdf/1784.1920'), (5,4))
        self.assertEqual(t.match('arxiv.org/pdf/2340.0124'), (0,0))
        self.assertTrue(t.predict_success('arxiv.org/pdf/1784.1920', threshold=0.6, min_urls=3))
        t.print_as_tree()

    def test_prune_failures(self):
        t = PrefTree()
        for url, success in [
                ('sciencedirect.com/paper1.pdf', False),
                ('sciencedirect.com/paper2.pdf', False),
                ('sciencedirect.com/paper3.pdf', False),
                ('mysciencework.com/paper9.pdf', True),
                ('mysciencework.com/paper8.pdf', False)]:
            t.add_url(url, success)
        t, pruned = t.prune(min_rate=0.95, min_children=2, min_urls=2)
        self.assertEqual(t.match('sciencedirect.com/paper4.pdf'), (3,0))
        self.assertFalse(t.predict_success('sciencedirect.com/paper4.pdf'))

    def test_prune_with_reverse(self):
        t = PrefTree()
        for url, success in [
            ('researchgate.net/publication/233865122_uriset', False),
            ('researchgate.net/publication/143874230_albtedru', False),
            ('researchgate.net/publication/320748374_kelbcad', False),
            ('researchgate.net/publication/233865122_uriset.pdf', True),
            ('researchgate.net/publication/143874230_albtedru.pdf', True),
            ('researchgate.net/publication/320748374_kelbcad.pdf', True),
            ('onlinelibrary.wiley.com/wol1/doi/10.1002/anie.200800037.abstract', False),
            ('onlinelibrary.wiley.com/wol1/doi/10.1002/anie.200800037.pdf', False)]:
            t.add_url(url, success)
        t.print_as_tree()
        t, pruned = t.prune(reverse=True)
        t.print_as_tree()
        self.assertTrue(t.check_sanity())
        for u, c, s in t.urls():
            print flatten(u), c, s

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

class PrevPrefTreeTest(unittest.TestCase):
    def test_create(self):
        t = RevPrefTree()
        for url, success in [
            ('researchgate.net/publication/233865122_uriset', False),
            ('researchgate.net/publication/143874230_albtedru', False),
            ('researchgate.net/publication/320748374_kelbcad', False),
            ('researchgate.net/publication/233865122_uriset.pdf', True),
            ('researchgate.net/publication/143874230_albtedru.pdf', True),
            ('researchgate.net/publication/320748374_kelbcad.pdf', True),
            ]:
            t.add_url(url, success)
        t, pruned = t.prune()
        t.print_as_tree()
        self.assertEqual(len(t.urls()), 4)
        self.assertEqual(t.match('researchgate.net/publication/7489168_lopdetu.pdf'),
                (3,3))

class URLFilterTest(unittest.TestCase):
    def test_predict(self):
        f = URLFilter(prune_delay=5,min_urls_prediction=1,min_urls_prune=3)
        urls = [
            ('http://researchgate.net/publication/233865122_uriset', False),
            ('http://researchgate.net/publication/143874230_albtedru', False),
            ('http://eprints.soton.ac.uk/pub/enrstancs.pdf', True),
            ('http://eprints.soton.ac.uk/pub/enrstancs/abs', False),
            ('http://researchgate.net/publication/233865122_uriset.pdf', True),
            ('http://researchgate.net/publication/942758431_plecuste', False),
            ('http://onlinelibrary.wiley.com/wol1/doi/10.1002/anie.200800037.abstract', False),
            ('http://researchgate.net/publication/320748374_kelbcad.pdf', True),
            ('http://researchgate.net/publication/942758431_plecuste.pdf', True),
            ('http://hal.archives-ouvertes.fr/hal-47198374', False),
            ('http://hal.archives-ouvertes.fr/hal-47198374/document', True),
            ('http://onlinelibrary.wiley.com/wol1/doi/10.1002/anie.200800037.pdf', False),
            ('http://researchgate.net/publication/617445243_bcldecry', False),
            ('http://researchgate.net/publication/320748374_kelbcad', False),
            ('http://hal.archives-ouvertes.fr/hal-3281748', False),
            ('http://hal.archives-ouvertes.fr/hal-0492738/document', True),
            ('http://researchgate.net/publication/143874230_albtedru.pdf', True),
            ('http://researchgate.net/publication/617445243_bcldecry.pdf', True),
            ]
        for url, success in urls:
            f.add_url(url, success)
        f.t.print_as_tree()
        self.assertTrue(f.t.check_sanity())
        self.assertFalse(f.predict_success('http://hal.archives-ouvertes.fr/hal-324581'))
        self.assertTrue(f.predict_success('http://hal.archives-ouvertes.fr/hal-429838/document'))
        self.assertTrue(f.predict_success('http://researchgate.net/publication/482893_erscbderl.pdf'))
        self.assertEqual(f.predict_success('http://eprints.soton.ac.uk/pub/oldcest.pdf'),
                None)


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(urltheory.tokenizer))
    tests.addTests(doctest.DocTestSuite(urltheory.utils))
    return tests

