# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
from .forest import URLForest
from urltheory.utils import confidence
from urltheory.utils import proba_confidence
from urltheory import tokenizer
import requests
from requests.models import REDIRECT_STATI
from accesspredict.utils import normalize_outgoing_url
from accesspredict.statistics import CrawlingStatistics

crawler_user_agent = 'http://dissem.in/'

class Spider(object):
    """
    Holds an URL forest and a set of associated predictors.
    """
    def __init__(self, forest=None, dataset=None, stats=None):
        self.forest = forest or URLForest()
        self.dataset = dataset # We don't necessarily need a dataset
        self.predictors = {}
        self.stats = stats or CrawlingStatistics()
        self.smoothing = {}

    def __contains__(self, key):
        return key in self.predictors

    def incr(self, key):
        """
        Shortcut to increment statistics
        """
        self.stats.increment(key)

    def add_predictor(self, class_id, predictor, smoothing, tree=None):
        """
        Adds a predictor for the given class_id
        The tree identified by class_id from the forest will be
        used, unless there is none, in which case the tree provided
        will be used.

        :param smoothing: the smoothing value (pair of floats) for this predictor
        """
        if class_id in self:
            raise ValueError('We already have a tree for "%s"' % class_id)
        predictor.set_spider(self)
        self.predictors[class_id] = predictor
        if tree is not None and class_id in self.forest:
            raise ValueError('A tree for "%s" already exists.' % class_id)
        elif class_id not in self.forest:
            self.forest.add_tree(class_id, tree)

        self.smoothing[class_id] = smoothing

        # init the stats for this class
        if self.stats:
            for key in ['incoming','cached','pre_filter','post_filter','filtered',
                        'requested','redirected','learned']:
                self.stats.add_key('%s:%s' % (class_id,key))

    def predict(self, class_id, url, history=[], referer=None, min_confidence=0.8):
        """
        Predicts the membership of an URL to a class.

        :param class_id: the class membership to test for
        :param url: the URL to classify
        :param history: history of previous requests, input
                as a list of (url, tokenized). These URLs should
                only be accumulated as the result of HTTP redirects.
        :param referer: any referer to provide as a header
        :param min_confidence: discard cached or inferred results with a
                confidence lower than this threshold, and ask
                the classifier to return a result with a better
                confidence. Setting this parameter to anything above one
                should force all downloads involved.
        :returns: the (smoothed) probability that the url belongs to the class
        """
        if class_id not in self:
            raise ValueError('No predictor for class "%s".' % class_id)
        predictor = self.predictors[class_id]

        self.incr(class_id+':incoming')

        # Coerce to unicode
        if type(url) != unicode:
            url = url.decode('utf-8')

        # Normalize the URL and check if we haven't checked it yet
        if self.dataset is not None:
            previous_result = self.dataset.get_if_recent(url, class_id)
            if previous_result is not None:
                previous_confidence = proba_confidence(previous_result)
                if previous_confidence > min_confidence:
                    self.incr(class_id+':cached')
                    return previous_result

        tokenized = tokenizer.prepare_url(url)

        # first check if it's obvious from the URL
        pre_url_answer = predictor.predict_before_filter(url, tokenized,
                                min_confidence=min_confidence)
        if pre_url_answer is not None:
            # In this case, the classification is obvious from the url.
            # There is no point in adding this particular URL to the
            # prefix tree as it is efficiently filtered out by this
            # method. But, we want to update the URLs in the history
            # because they involved making expensive HTTP requests.
            self._update_history_classification(class_id, history, pre_url_answer)
            self.incr(class_id+':pre_filter')
            return pre_url_answer

        # then check if the prefix tree predicts a category
        answer = self._get_preftree_answer(class_id, tokenized, min_confidence)

        if answer is not None and proba_confidence(answer) > min_confidence:
            print "## skipped %s" % url
            print "   answer: %f" % answer
            self.incr(class_id+':filtered')
            return answer

        new_history = history + [(url, tokenized)]

        # check again from the URL, allowing for longer (because cached by us) checks
        post_filter_url_answer = predictor.predict_before_fetch(url, tokenized,
                    min_confidence=min_confidence)
        if post_filter_url_answer is not None:
            # this time the history contains the current url
            self._update_history_classification(class_id, new_history, post_filter_url_answer)
            self.incr(class_id+':post_filter')
            return post_filter_url_answer

        # otherwise, fetch and classify manually
        answer = False # by default
        try:
            kwargs = {
                'allow_redirects':False,
                'timeout':10,
                'stream':predictor.stream_mode,
            }
            headers = {
                'User-Agent': crawler_user_agent,
            }
            if referer:
                headers['Referer'] = referer

            self.incr(class_id+':requested')

            print "## fetching %s" % url
            if predictor.head_mode:
                r = requests.head(url, **kwargs)
            else:
                r = requests.get(url, **kwargs)

            r.raise_for_status()

            # detect redirects
            next_url = r.headers.get('location')
            if r.status_code in REDIRECT_STATI and next_url:
                # detect cyclic redirects
                if (next_url in [url for url, t in history] or
                    len(history) > 15):
                    raise requests.exceptions.TooManyRedirects()

                next_url = normalize_outgoing_url(r.url, next_url)
                self.incr(class_id+':redirected')
                return self.predict(class_id, next_url, new_history,
                            min_confidence=min_confidence, referer=referer)

            # classify manually
            answer = predictor.predict_after_fetch(r, url, tokenized, min_confidence)
        except requests.exceptions.RequestException:
            pass
        except UnicodeDecodeError:
            pass

        self._update_history_classification(class_id, new_history, answer)
        return answer

    def _update_history_classification(self, class_id, history, status):
        """
        Given a list of (url, tokenized), and a boolean status,
        add all urls in the history to the prefix tree with the given
        status
        """
        for url, tokenized in history:
            self.incr(class_id+':learned')
            if self.dataset is not None:
                self.dataset.set(url, class_id, status)
            # TODO: this involves acquiring and releasing many times
            # the same lock. Add a method in URLForest to add many URLs
            # that acquires the lock only once.
            self.forest.add_url(class_id, tokenized, status)

    def _get_preftree_answer(self, class_id, tokenized, min_confidence):
        """
        Given a tokenized URL, returns
        a boolean if the prefix tree predicts
        a class, or None if a manual classification is
        needed
        """
        url_count, success_count = self.forest.match(class_id,
            tokenized, maximum_confidence=True)

        if not url_count:
            return None

        obtained_confidence = confidence(url_count, success_count, self.smoothing[class_id])
        print "threshold: %f" % min_confidence
        print "count: %d/%d" % (success_count, url_count)
        print "confidence: %f" % obtained_confidence
        if obtained_confidence > min_confidence:
            return 2*success_count >= url_count



