# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

class URLCategoryPredictor(object):
    """
    Predictor for a particular category (e.g. PDF files)

    The k parameter controls how often we fetch the content
    of the URL for checking. The higher it is, the more often
    we check.
    """
    # perform requests in stream mode
    stream_mode = True
    # perform HEAD requests instead of GET
    head_mode = False

    def __init__(self, spider=None):
        """
        :param spider: binds the predictor to a spider,
            if recursion is needed.
        """
        super(URLCategoryPredictor, self).__init__()
        self.spider = spider

    def predict_before_filter(self, url, tokenized_url):
        """
        To be overriden by the actual classification code.
        This method should not fetch the URL: it should only
        return a boolean when the content of the URL can
        be classified from the URL itself.

        This method should be very very quick to run,
        like matching the URL with a few regexps.
        For longer processing that is worth being cached
        by the URL filter, use predict_before_fetch.

        :param url: the URL to classify
        :param tokenized_url: a tokenized version of the URL
        :returns: a boolean indicating if the document belongs
                 to the category, or None if we can't tell from
                 the URL only
        """
        return None

    def predict_before_fetch(self, url, tokenized_url):
        """
        To be overriden by the actual classification code.
        This method can be more heavy than predict_before_filter
        but should not fetch the URL itself.

        :param url: the URL to classify
        :param tokenized_url: a tokenized version of the URL
        :returns: a boolean indicating if the document belongs
                 to the category, or None if we can't tell from
                 the URL only
        """
        return None

    def predict_after_fetch(self, request, url, tokenized):
        """
        To be overriden by the actual classification code.

        :param request: the request we have used to fetch it
        :param url: the original URL we tried to fetch
        :param tokenized: the tokenized version of that URL
        :returns: a boolean indicating if the document
                  belongs to the category.
        """
        return False


