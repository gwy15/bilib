import unittest

import bilib

from tests import config


class UserTester(unittest.TestCase):
    def setUp(self):
        self.config = config.getConfig()
        self.user = bilib.User(self.config['phone'], self.config['password'])

    def testInit(self):
        with self.assertRaises(TypeError):
            bilib.User(12300001234, '123', '123')
        with self.assertRaises(TypeError):
            bilib.User('1230001234', 123, '123')
        with self.assertRaises(TypeError):
            bilib.User('1230001234', '123', 123)
        with self.assertRaises(TypeError):
            bilib.User('1230001234', '123', '123', level='1')
        with self.assertRaises(TypeError):
            bilib.User('1230001234', '123', '123', coins='1')

    def testDanmu(self):
        danmu = bilib.Danmu(
            'test', 2_000,  # 2s
            self.config['danmu']['aid'],
            self.config['danmu']['cid'])

        with self.assertRaises(bilib.user.BiliRequireLogin):
            self.user.postDanmu(danmu)

        self.user.login()
        self.user.postDanmu(danmu)

        with self.assertRaises(TypeError):
            self.user.postDanmu(123)

    def testUserInfo(self):
        with self.assertRaises(bilib.user.BiliRequireLogin):
            self.user.csrf

        with self.assertRaises(bilib.user.BiliRequireLogin):
            self.user.getUserInfo()

        self.user.login()
        self.assertEqual(self.user.name, self.config['username'])

        self.assertIsInstance(self.user.level, int)
        self.assertIsInstance(self.user.coins, int)
        self.assertIsInstance(self.user.name, str)
        self.assertIsInstance(self.user.csrf, str)

    def testUpdateCoin(self):
        with self.assertRaises(bilib.user.BiliRequireLogin):
            self.user.updateCoins()

        self.user.login()
        self.user.updateCoins()

    @unittest.skip('投币不能测试太多')
    def testGiveCoin(self):
        with self.assertRaises(bilib.user.BiliRequireLogin):
            self.user.giveCoin(24145781)

        self.user.login()

        with self.assertRaises(TypeError):
            self.user.giveCoin('24145781')
        with self.assertRaises(TypeError):
            self.user.giveCoin(24145781, '1')
        with self.assertRaises(ValueError):
            self.user.giveCoin(24145781, 3)

        self.user.giveCoin(24145781)
