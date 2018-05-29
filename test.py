import unittest

if __name__ == '__main__':
    discover = unittest.defaultTestLoader.discover(
        'tests', pattern='test*.py')
    runner = unittest.TextTestRunner()
    if not runner.run(discover).wasSuccessful():
        exit(1)
