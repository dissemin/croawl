import unittest

from .pdfpredictor import PDFPredictor

class PDFPredictorTest(unittest.TestCase):
    def check_url(self, url, expected):
        import requests
        p = PDFPredictor()
        value = p.predict_after_fetch(requests.get(url), url, None)
        self.assertEqual(value, expected)

    def test_pdf(self):
        self.check_url('https://arxiv.org/pdf/1611.07004.pdf', 1.)

    def test_psgz(self):
        self.check_url('http://cds.cern.ch/record/682079/files/larg-96-064.ps.gz', 1.)

    def test_djvu(self):
        self.check_url('http://bibliotekacyfrowa.eu/Content/25196/027048-0001.djvu', 1.)

    def test_html(self):
        self.check_url('http://www.die-bonn.de/id/17041_p1/about/html/?lang=de', 0.)

    def test_targz(self):
        self.check_url('http://gdac.broadinstitute.org/runs/analyses__2014_07_15/data/PAAD-TP/20140715/gdac.broadinstitute.org_PAAD-TP.mRNAseq_Clustering_CNMF.Level_4.2014071500.0.0.tar.gz', 0.)

    def test_junk(self):
        self.check_url('https://www.linkedin.com/start/join?trk=login_reg_redirect&session_redirect=https%3A%2F%2Fwww.linkedin.com%2Fsharing%2Fshare-offsite%3Fmini%3Dtrue%26url%3Dhttps%253A%252F%252Flink.springer.com%252Farticle%252F10.1007%252FBF02433744%26title%3DDruckmessungen%2520im%2520linken%2520Vorhof%2520nach%2520dem%2520Verschlu%25C3%259F%2520eines%2520Vorhofseptumdefektes%26summary%3DNo%2520Abstract%2520available%2520for%2520this%2520article',
            0.)
