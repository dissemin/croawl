# -*- encoding: utf-8 -*-


import unittest
import doctest
from hashable_collections.hashable_collections import hashable_list

import urltheory
from urltheory.tokenizer import *
from urltheory.preftree import PrefTree, RevPrefTree
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

    def test_match(self):
        t = PrefTree()
        urls = [
                ('aab/ced',True),
                ('aab/ru',False),
                ('bcadr/ste',False),
                ('aab/t/est',True),
                ('aab/t/le',True),
                ('aab/stts',False),
                ]
        for u, s in urls:
            t.add_url(u, s)
        t, pruned = t.prune(confidence_threshold=0.1)

        c, s, b = t.match_with_branch('aab/t/lu')
        self.assertEqual((c,s),(2,2))
        self.assertEqual(''.join(b), 'aab/t/*')

        c, s, b = t.match_with_branch('aab/xx')
        self.assertEqual((c,s),(0,0))
        self.assertEqual(''.join(b), 'aab/<unk>')

        c, s, b = t.match_with_branch('aab/ced')
        self.assertEqual((c,s),(1,1))
        self.assertEqual(''.join(b), 'aab/ced')

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
            t.prune(confidence_threshold=0)

        for url, success in [
                ('arxiv.org/pdf/1410.1234', True),
                ('arxiv.org/pdf/1409.1094', True),
                ('arxiv.org/pdf/1201.5480', True),
                ('arxiv.org/pdf/1601.01234', True),
                ('arxiv.org/pdf/1602.01i34', False), # oops
                ('gnu.org/about.html', False),
                ]:
            t.add_url(url, success)
        t, pruned = t.prune(confidence_threshold=0.05)
        t.print_as_tree()
        self.assertEqual(len(t.urls()), 2)
        self.assertTrue(t.has_wildcard())
        self.assertEqual(t.match('arxiv.org/pdf/1784.1920'), (5,4))
        self.assertEqual(t.match('arxiv.org/pdf/2340.0124'), (0,0))

        self.assertEqual(t.generate_regex(
                confidence_threshold=0.05), 'arxiv\.org\/pdf\/1.*')

    def test_no_prune(self):
        t = PrefTree()
        t.add_url('gnu.org/about.html', False)
        t.add_url('arxiv.org/pdf/1234.6789', True)
        t.add_url('zenodo.org/record/1278/', True)
        t, pruned = t.prune(confidence_threshold=0.3)
        self.assertFalse(pruned)
        self.assertFalse(t.has_wildcard())

    def test_prune_failures(self):
        t = PrefTree()
        for url, success in [
                ('sciencedirect.com/paper1.pdf', False),
                ('sciencedirect.com/paper2.pdf', False),
                ('sciencedirect.com/paper3.pdf', False),
                ('mysciencework.com/paper9.pdf', True),
                ('mysciencework.com/paper8.pdf', False)]:
            t.add_url(url, success)
        t, pruned = t.prune(confidence_threshold=0.2)
        self.assertEqual(t.match('sciencedirect.com/paper4.pdf'), (3,0))

    def test_prune_empty(self):
        t = PrefTree()
        t, pruned = t.prune()
        self.assertFalse(pruned)

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
            print(flatten(u), c, s)

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

    def test_init(self):
        with self.assertRaises(ValueError):
            PrefTree(url_count=-1)

        with self.assertRaises(ValueError):
            PrefTree(success_count=-1)

        with self.assertRaises(ValueError):
            PrefTree(url_count=1, success_count=2)

    def test_check_sanity(self):
        t = PrefTree()
        t['abc'] = PrefTree()
        t['aa'] = PrefTree()
        self.assertFalse(t.check_sanity())

        t = PrefTree(url_count=0)
        t.url_count = -1
        self.assertFalse(t.check_sanity())

        t = PrefTree()
        t['abc'] = PrefTree()
        t.is_wildcard = True
        self.assertFalse(t.check_sanity())

        t2 = PrefTree()
        t2['def'] = t
        self.assertFalse(t2.check_sanity())

    def test_regex(self):
        t = PrefTree()
        for url, success in [
            ('researchgate.net/publication/233865122_uriset', False),
            ('researchgate.net/publication/143874230_albtedru', False),
            ('researchgate.net/publication/320748374_kelbcad', False),
            ('researchgate.net/publication/233865122_uriset.pdf', True),
            ('researchgate.net/publication/143874230_albtedru.pdf', True),
            ('researchgate.net/publication/320748374_kelbcad.pdf', True),
            ('erudit.org/get_file?name=test.pdf', False),
            ('erudit.org/get_file?name=document.pdf', False),
            ('erudit.org/get_file?name=article.pdf', False),
            ]:
            t.add_url(url, success)
        t, pruned = t.prune(confidence_threshold=0.2, reverse=True)
        t.print_as_tree()
        self.assertEqual(t.generate_regex(confidence_threshold=0.2),
                        'researchgate\.net\/publication\/.*\.pdf')

class RevPrefTreeTest(unittest.TestCase):
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
        t, pruned = t.prune(confidence_threshold=0.1)
        self.assertEqual(len(t.urls()), 4)
        self.assertEqual(t.match('researchgate.net/publication/7489168_lopdetu.pdf'),
                (3,3))
        self.assertEqual(t.generate_regex(confidence_threshold=0.1), '.*\.pdf')

def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(urltheory.tokenizer))
    tests.addTests(doctest.DocTestSuite(urltheory.utils))
    return tests

