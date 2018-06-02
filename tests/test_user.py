import unittest

import bilib

from tests import config


class ErrorTest(unittest.TestCase):
    def testRepr(self):
        self.assertEqual(repr(bilib.user.BiliError('reason')),
                         '<BiliError: reason>')
        self.assertEqual(repr(bilib.user.BiliRequireLogin('reason')),
                         '<BiliRequireLogin: reason>')


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

    @unittest.skip('发送弹幕太快跳过')
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

    def testStr(self):
        self.assertEqual(
            str(self.user),
            f'<bilib.User {self.user.phone} [not logged in]>')

        self.user.login()

        self.assertEqual(
            str(self.user),
            f'<bilib.User {self.user.phone} lv.{self.user.level}>')

    def testDo(self):
        with self.assertRaises(bilib.user.BiliError):
            import requests
            self.user.do(requests.get, 'http://www.non-exist.com/index.html')

    @unittest.skip('评论也不能测试太多')
    def testComment(self):
        with self.assertRaises(bilib.user.BiliRequireLogin):
            self.user.comment(24110743)

        # TODO: 补全测试
