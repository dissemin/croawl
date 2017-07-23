# -*- encoding: utf-8 -*-

#import PyPDF2
#from PyPDF2.utils import PyPdfError
import contextlib
import re
import unittest
import zlib
from io import StringIO
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
    b'AT&TFORM.*DJVM', # djvu. DJVU can also be used in place of DJVM
                             # but that's for one-page documents, so
                             # excluded here
    b'\012?%PDF', # pdf
    b'\004?%!', # postscript
]

gzip_file_prefix_re = re.compile(b'\037\213')

acceptable_file_start_re = re.compile(
    b'('+ (b'|'.join(acceptable_file_prefixes)) + b')')

class PDFPredictor(URLCategoryPredictor):
    """
    Predictor for PDF files.
    """
    stream_mode = True
    min_pages = 3
    max_pdf_size = 1024*1024*50

    def predict_after_fetch(self, request, url, tokenized, min_confidence=0.8):
        """
        Parses the PDF file.

        :para min_confidence: ignored because this predictor only returns
                                0 or 1, which have confidence 1
        """
        with contextlib.closing(request) as request:
            try:  # We try to extract the first page of the PDF
                if (int(request.headers.get('content-length', 0)) >
                    self.max_pdf_size):
                    return 0.

                # check that the content-type looks legit
                content_type = request.headers.get('content-type')
                if not any(content_type.startswith(c)
                            for c in allowed_content_types):
                    return 0.

                for chunk in request.iter_content(chunk_size=1024):
                    data = chunk
                    compressed = (gzip_file_prefix_re.match(data) is not None)
                    if compressed:
                        d = zlib.decompressobj(zlib.MAX_WBITS|32)
                        data = d.decompress(chunk, 32)
                    return float(acceptable_file_start_re.match(data) is not None)

                # Old code that downloads the whole PDF and parses it
                #f = StringIO(request.content)
                #reader = PyPDF2.PdfFileReader(f)
                #return (not reader.isEncrypted and
                #        reader.getNumPages() >= self.min_pages)
            except (ValueError, zlib.error) as e:
                print(e)
                # PyPDF2 failed (maybe it believes the file is encrypted…)
                return 0.




