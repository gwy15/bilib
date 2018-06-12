import logging
import unittest

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    discover = unittest.defaultTestLoader.discover(
        'tests', pattern='test*.py')
    runner = unittest.TextTestRunner()
    exit(not runner.run(discover).wasSuccessful())
