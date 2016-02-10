# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from StringIO import StringIO
import PyPDF2
from PyPDF2.utils import PyPdfError

def check_pdf(pdf_blob):
    """
    Check that a string represents a valid PDF file.
    """
    try: # We try to extract the first page of the PDF
        orig_pdf = StringIO(pdf_blob)
        reader = PyPDF2.PdfFileReader(orig_pdf)
        num_pages = reader.getNumPages()
        if not reader.isEncrypted and num_pages == 0:
            return False
        return True
    except (PyPdfError, ValueError) as e:
        # PyPDF2 failed (maybe it believes the file is encrypted…)
        return False


