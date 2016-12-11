# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
import json
import requests
import os
import re
import binascii
from .predictor import URLCategoryPredictor
from .pdfpredictor import PDFPredictor

class ZoteroFullTextPredictor(URLCategoryPredictor):
    """
    Predictor for PDF files.
    """
    head_mode = True
    zotero_endpoint = 'http://localhost:1969/web'
    allowed_content_types = re.compile('text/html.*')

    def __init__(self, pdf_predictor=None, **kwargs):
        super(ZoteroFullTextPredictor, self).__init__(**kwargs)
        self.pdf_predictor = pdf_predictor or PDFPredictor()

    def find_full_text(self, json_resp):
        for idx, item in enumerate(json_resp):
            for attachment in item.get('attachments',[]):
                url = attachment.get('url')
                if (attachment.get('mimeType') == 'application/pdf'
                    and url
                    and  self.pdf_predictor.filtered_predict(url)):
                    return True
        return False

    def predict_after_fetch(self, request, url, tokenized):
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
            return False

        try:
            r = requests.post(self.zotero_endpoint,
                    headers=headers,
                    data=json.dumps(zotero_data))
            r.raise_for_status()
            json_resp = r.json()
            return self.find_full_text(json_resp)
        except (ValueError, requests.exceptions.RequestException) as e:
            print e
            return False

