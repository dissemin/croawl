# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
#import PyPDF2
#from PyPDF2.utils import PyPdfError
import contextlib
import re
from StringIO import StringIO
from .predictor import URLCategoryPredictor

blacklisted_content_types = [
    'text/html',
    'text/xml',
    'application/xhtml+xml',
    'image/jpeg',
    'image/jpg',
    'image/png',
    'application/x-tika-ooxml',
]

unsupported_content_types = [
    'application/msword',
]

allowed_content_types = [
    'application/download',
    'application/x-download',
    'application/octet-stream',
    'application/pdf',
    'image/x.djvu',
    'image/vnd.djvu',
    'application/postscript',
]

acceptable_file_prefixes = [
    r'AT&TFORM.*DJVM', # djvu. DJVU can also be used in place of DJVM
                             # but that's for one-page documents, so
                             # excluded here
    r'\012?%PDF', # pdf
    r'\004?%!', # postscript
]
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
                    acceptable = acceptable_file_start_re.match(chunk) is not None
                    return acceptable

                # Old code that downloads the whole PDF and parses it
                #f = StringIO(request.content)
                #reader = PyPDF2.PdfFileReader(f)
                #return (not reader.isEncrypted and
                #        reader.getNumPages() >= self.min_pages)
            except (PyPdfError, ValueError) as e:
                # PyPDF2 failed (maybe it believes the file is encrypted…)
                pass


