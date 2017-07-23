# -*- encoding: utf-8 -*-

import json
import requests
import os
import re
import binascii
from lxml import html
from lxml import etree
from requests.compat import urlparse
from .predictor import URLCategoryPredictor
from .utils import normalize_outgoing_url
from .pdfpredictor import allowed_content_types as pdf_content_types
from .pdfpredictor import acceptable_file_start_re as pdf_file_start_re

identifiers_re = re.compile(
    r'(10\.[0-9]{4,}[^ ]*/[^ &]+|[0-9][0-9._\-/:]+[0-9])')


class ScraperFullTextPredictor(URLCategoryPredictor):
    """
    Tries to find a PDF link in a webpage
    (also accepts direct links to PDFs)
    """
    allowed_content_types = pdf_content_types + ['text/html']

    def extract_good_links(self, url, content):
        """
        Extract links that could lead to a PDF. It should be
        an over-approximation as we will later check that they
        lead to a PDF file (with a filter).
        """
        try:
            root = html.fromstring(content)
        except etree.XMLSyntaxError:
            return

        # Use any link if it shares any identifier with
        # the current URL.
        target_identifiers = set(identifiers_re.findall(url))
        print(target_identifiers)
        for link in self.meta_and_a_links(root):
            identifiers = set(identifiers_re.findall(link))
            if identifiers & target_identifiers:
                yield link

    def meta_and_a_links(self, root):
        """
        Extract all <meta /> and <a /> links
        """
        for link in root.xpath("//head/link[@rel='alternate']"):
            yield link.attrib.get('href', '')
        for meta in root.xpath('//head/meta'):
            yield meta.attrib.get('content', '')
        for a in root.xpath('//a'):
            yield a.attrib.get('href', '')

    def normalize_urls(self, orig_url, new_urls):
        """
        Remove Nones, link resolvers, absolutifies urls…
        """
        for new_url in new_urls:
            if not new_url:
                continue
            new_url = normalize_outgoing_url(orig_url, new_url.strip())
            if not new_url:
                print("INVALID URL:")
                print(orig_url)
                print(new_url)
                continue
            parsed = urlparse(new_url)
            if not parsed.hostname:
                continue
            if orig_url == new_url:
                continue
            yield new_url


    def predict_after_fetch(self, request, url, tokenized,
                            min_confidence=0.8):
        """
        Tries to find a sensible PDF link.
        """
        content_type = request.headers.get('content-type', 'unknown')
        content_type_allowed = any(
            content_type.startswith(c)
            for c in self.allowed_content_types)
        if not content_type_allowed:
            return 0.

        if content_type.startswith('text/html'):
            links = self.extract_good_links(url, request.content)
            links = set(self.normalize_urls(url, links))
            print("~~ URLs extracted from %s" % url)
            for l in links:
                print(l)
            print("~~~")

            return max([self.spider.predict('pdf', pdf_url,
                       referer=url, min_confidence=min_confidence)
                        for pdf_url in links], 0.)
        else: # we are dealing with a candidate PDF file
            for chunk in request.iter_content(chunk_size=1024):
                return float(pdf_file_start_re.match(chunk) is not None)


