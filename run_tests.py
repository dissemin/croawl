import unittest
loader = unittest.defaultTestLoader.discover('.')
unittest.TextTestRunner().run(loader)
