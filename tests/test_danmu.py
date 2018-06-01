import unittest

import bilib

from tests import config


class DanmuTester(unittest.TestCase):
    def setUp(self):
        self.config = config.getConfig()

    def testDanmuGetCid(self):
        t = 12000
        danmu = bilib.Danmu('test', t, self.config['danmu']['aid'])
        self.assertEqual(danmu.cid, self.config['danmu']['cid'])

    def testDanmuStr(self):
        aid, cid = 1551, 1551
        cases = ((12, '0.012'),
                 (123, '0.123'),
                 (1_234, '1.234'),
                 (12_345, '12.345'),
                 (70_234, '1:10.234'),
                 (121_234, '2:01.234'),
                 (1201_234, '20:01.234'),
                 (3601_234, '1:00:01.234'),
                 (36062_234, '10:01:02.234'))
        for case in cases:
            with self.subTest(case=case):
                danmu = bilib.Danmu('test', case[0], aid, cid)
                self.assertEqual(
                    str(danmu), f'<Danmu "test" @{case[1]} #{aid}>')
