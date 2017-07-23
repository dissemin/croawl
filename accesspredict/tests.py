import doctest
import accesspredict
from accesspredict.smoothing import ExponentialDirichlet

def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(accesspredict.smoothing))
    return tests

