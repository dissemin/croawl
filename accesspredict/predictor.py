# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
from urltheory.preftree import PrefTree
from urltheory.utils import confidence
from urltheory import tokenizer
import random
import requests
from requests.compat import urlparse, urljoin
from requests.utils import requote_uri

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

    def __init__(self, k=1):
        super(URLCategoryPredictor, self).__init__()
        if k <= 0:
            raise ValueError('k has to be positive')
        self.k = k
        self.t = PrefTree()

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

    def predict(self, url, force=False, history=[]):
        """
        Predicts the status of a URL, but first
        check with the URLFilter.

        :param url: the URL to classify
        :param force: ignore the current URL filter
        :param history: history of previous requests, input
                as a list of (url, tokenized)
        """
        tokenized = tokenizer.prepare_url(url)

        # first check if it's obvious from the URL
        pre_url_answer = self.predict_before_filter(url, tokenized)
        if pre_url_answer is not None:
            # In this case, the classification is obvious from the url.
            # There is no point in adding this particular URL to the
            # prefix tree as it is efficiently filtered out by this
            # method. But, we want to update the URLs in the history
            # because they involved making expensive HTTP requests.
            self.update_history_classification(history, pre_url_answer)
            return pre_url_answer

        # then check if the prefix tree predicts
        # a category
        answer = self.get_preftree_answer(tokenized)
        
        if answer is not None:
            print "## skipped %s" % url
            print "   answer: %s" % unicode(answer)
            return answer
        
        new_history = history + [(url, tokenized)]

        # check again from the URL, allowing for longer (cached) checks
        post_filter_url_answer = self.predict_before_fetch(url, tokenized)
        if post_filter_url_answer is not None:
            # this time the history contains the current url
            self.update_history_classification(history, pre_url_answer)
            return post_url_answer
        
        # otherwise, fetch and classify manually
        answer = False # by default
        try:
            kwargs = {
                'allow_redirects':False,
                'timeout':10,
                'stream':self.stream_mode,
            }
            print "## fetching %s" % url
            if self.head_mode:
                r = requests.head(url, **kwargs)
            else:
                r = requests.get(url, **kwargs)

            r.raise_for_status()
            
            # detect redirects
            if r.status_code >= 300 and r.status_code < 400:
                next_url = r.headers.get('location')
                # detect cyclic redirects
                if (next_url in [url for url, t in history] or
                    len(history) > 10):
                    raise requests.exceptions.TooManyRedirects()

                # code adapted from the requests lib
                if next_url.startswith('//'):
                    parsed_rurl = urlparse(r.url)
                    next_url = '%s:%s' % (parsed_rurl.scheme, url)

                parsed = urlparse(next_url)
                next_url = parsed.geturl()

                if not parsed.netloc:
                    next_url = urljoin(r.url, requote_uri(next_url))
                else:
                    next_url = requote_uri(next_url)
                # end adapted code

                return self.predict(next_url, new_history)

            # classify manually
            answer = self.predict_after_fetch(r, url, tokenized)
        except requests.exceptions.RequestException:
            pass

        self.update_history_classification(new_history, answer)
        return answer

    def update_history_classification(self, history, status):
        """
        Given a list of (url, tokenized), and a boolean status,
        add all urls in the history to the prefix tree with the given
        status
        """
        for url, tokenized in history:
            self.t.add_url(tokenized, status)

    def get_preftree_answer(self, tokenized):
        """
        Given a tokenized URL, returns
        a boolean if the prefix tree predicts
        a class, or None if a manual classification is
        needed
        """
        threshold = 0.7 + 0.3*random.random()

        url_count, success_count = self.t.match(tokenized,
            confidence_threshold=threshold)
        
        if not url_count:
            return None
 
        obtained_confidence = confidence(url_count, success_count)
        print "threshold: %f" % threshold
        print "count: %d/%d" % (success_count, url_count)
        print "confidence: %f" % obtained_confidence
        if obtained_confidence > threshold:
            return 2*success_count >= url_count

