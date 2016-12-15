# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
#import PyPDF2
#from PyPDF2.utils import PyPdfError
import contextlib
import re
import unittest
import zlib
from StringIO import StringIO
from .predictor import URLCategoryPredictor

allowed_content_types = [
    'application/download',
    'application/x-download',
    'application/octet-stream',
    'application/pdf',
    'image/x.djvu',
    'image/vnd.djvu',
    'application/postscript',
    'application/ps',
]

acceptable_file_prefixes = [
    r'AT&TFORM.*DJVM', # djvu. DJVU can also be used in place of DJVM
                             # but that's for one-page documents, so
                             # excluded here
    r'\012?%PDF', # pdf
    r'\004?%!', # postscript
]

gzip_file_prefix_re = re.compile(r'\037\213')

acceptable_file_start_re = re.compile(
    '(%s)' % ('|'.join(acceptable_file_prefixes)))

class PDFPredictor(URLCategoryPredictor):
    """
    Predictor for PDF files.
    """
    stream_mode = True
    min_pages = 3
    max_pdf_size = 1024*1024*50

    def predict_after_fetch(self, request, url, tokenized):
        """
        Parses the PDF file
        """
        with contextlib.closing(request) as request:
            try:  # We try to extract the first page of the PDF
                if (int(request.headers.get('content-length', 0)) >
                    self.max_pdf_size):
                    return False

                # check that the content-type looks legit
                content_type = request.headers.get('content-type')
                if not any(content_type.startswith(c)
                            for c in allowed_content_types):
                    return False

                for chunk in request.iter_content(chunk_size=1024):
                    data = chunk
                    compressed = (gzip_file_prefix_re.match(chunk) is not None)
                    if compressed:
                        d = zlib.decompressobj(zlib.MAX_WBITS|32)
                        data = d.decompress(chunk, 32)
                    return acceptable_file_start_re.match(data) is not None

                # Old code that downloads the whole PDF and parses it
                #f = StringIO(request.content)
                #reader = PyPDF2.PdfFileReader(f)
                #return (not reader.isEncrypted and
                #        reader.getNumPages() >= self.min_pages)
            except (ValueError, zlib.error) as e:
                print e
                # PyPDF2 failed (maybe it believes the file is encrypted…)
                return False



class PDFPredictorTest(unittest.TestCase):
    def test_url(self, url, expected):
        import requests
        p = PDFPredictor()
        value = p.predict_after_fetch(requests.get(url), url, None)
        self.assertEqual(value, expected)

    def test_pdf(self):
        self.test_url('https://arxiv.org/pdf/1611.07004.pdf', True)

    def test_psgz(self):
        self.test_url('http://cds.cern.ch/record/682079/files/larg-96-064.ps.gz', True)

    def test_djvu(self):
        self.test_url('http//bibliotekacyfrowa.eu/Content/25196/027048-0001.djvu', True)

    def test_html(self):
        self.test_url('http://www.die-bonn.de/id/17041_p1/about/html/?lang=de', False)

    def test_targz(self):
        self.test_url('http://gdac.broadinstitute.org/runs/analyses__2014_07_15/data/PAAD-TP/20140715/gdac.broadinstitute.org_PAAD-TP.mRNAseq_Clustering_CNMF.Level_4.2014071500.0.0.tar.gz',
False)
