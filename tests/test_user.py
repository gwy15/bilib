import unittest

import bililib

import config


class UserTester(unittest.TestCase):
    def setUp(self):
        self.config = config.getConfig()
        self.user = bililib.User(self.config['phone'], self.config['password'])

    def testDanmu(self):
        danmu = bililib.Danmu(
            'test', 2_000,  # 2s
            self.config['danmu']['aid'],
            self.config['danmu']['cid'])

        with self.assertRaises(bililib.user.BiliRequireLogin):
            self.user.postDanmu(danmu)

        self.user.login()
        self.user.postDanmu(danmu)

    def testUserInfo(self):

        with self.assertRaises(bililib.user.BiliRequireLogin):
            self.user.getUserInfo()

        self.user.login()
        self.assertEqual(self.user.name, self.config['username'])

        self.assertIsInstance(self.user.level, int)
        self.assertIsInstance(self.user.coins, int)
        self.assertIsInstance(self.user.name, str)
