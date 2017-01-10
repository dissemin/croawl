# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
import json
import requests
import os
import re
import binascii
from .predictor import URLCategoryPredictor

class ZoteroFullTextPredictor(URLCategoryPredictor):
    """
    Predictor for PDF files.
    """
    head_mode = True
    zotero_endpoint = 'http://localhost:1969/web'
    allowed_content_types = re.compile('text/html.*')

    def find_full_text(self, json_resp, min_confidence):
        if self.spider is None:
            raise ValueError('No spider has been provided.')

        probas = [0.]

        for idx, item in enumerate(json_resp):
            for attachment in item.get('attachments',[]):
                url = attachment.get('url')
                if (attachment.get('mimeType') == 'application/pdf'
                    and url):
                    probas.append(self.spider.predict('pdf', url,
                                min_confidence=min_confidence))
        return max(probas)

    def predict_after_fetch(self, request, url, tokenized,
                            min_confidence=0.8):
        """
        Checks that the content-type is plausible and sends
        the URL to the Zotero instance
        """
        headers = {'Content-Type': 'application/json'}
        zotero_data = {'url':url,
                'sessionid':binascii.hexlify(os.urandom(8))}

        content_type_allowed = self.allowed_content_types.match(
            request.headers.get('content-type', 'unknown'))
        if not content_type_allowed:
            return 0.

        try:
            r = requests.post(self.zotero_endpoint,
                    headers=headers,
                    data=json.dumps(zotero_data))
            r.raise_for_status()
            json_resp = r.json()
            return self.find_full_text(json_resp)
        except (ValueError, requests.exceptions.RequestException) as e:
            print e
            return 0.
