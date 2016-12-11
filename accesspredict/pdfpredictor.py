# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
import PyPDF2
from PyPDF2.utils import PyPdfError
import contextlib
from StringIO import StringIO
from .predictor import URLCategoryPredictor

class PDFPredictor(URLCategoryPredictor):
    """
    Predictor for PDF files.
    """
    stream_mode = True
    min_pages = 3
    max_pdf_size = 1024*1024*20

    def predict_after_fetch(self, request, url, tokenized):
        """
        Parses the PDF file
        """
        with contextlib.closing(request) as request:
            try:  # We try to extract the first page of the PDF
                if (int(request.headers.get('content-length', 0)) >
                    self.max_pdf_size):
                    return False
                f = StringIO(request.content)
                reader = PyPDF2.PdfFileReader(f)
                return (not reader.isEncrypted and
                        reader.getNumPages() >= self.min_pages)
            except (PyPdfError, ValueError) as e:
                # PyPDF2 failed (maybe it believes the file is encrypted…)
                pass


