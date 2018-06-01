import logging
import hashlib
import base64
import time
from urllib import parse
import json
import functools
import unittest

import requests
import rsa


class BiliError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg

    def __repr__(self):
        return '%s: %s' % (type(self).__name__, self.msg)


class BiliRequireLogin(BiliError):
    pass


class User:
    '''bilibili 用户基类

    实现登陆、发送弹幕、投币

    Args:
        phone (str): 用户登陆所用的电话号码。
        password (str): 用户的密码。
        username (str): 默认用户名，可以传入，但在调用 login() 方法后会自动拉取。
        level (int): 同 username。
        coins (int): 同 username。

    Raises:
        TypeError: 参数类型不符合。

    '''

    APPKEY = '1d8b6e7d45233436'
    SECRET_KEY = "560c52ccd288fed045859ed18bffd973"

    def __init__(self, phone, password, username=None, level=0, coins=0):
        self.session = None

        self.assertType(phone, 'phone', str)
        self.phone = phone

        self.assertType(password, 'password', str)
        self.password = password

        self.assertType(level, 'level', int)
        self.assertType(coins, 'coins', int)

        self.session = requests.session()

        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
        self.session.headers['Host'] = 'api.bilibili.com'
        self.session.headers['Origin'] = 'https://www.bilibili.com'
        self.session.headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        self.logined = False

        self.level = level
        self.coins = coins
        self.name = username if username else 'unlogined user'

        self.logger = logging.getLogger(self.phone)

    def __del__(self):
        if self.session:
            self.session.close()

    def __repr__(self):
        if not self.logined:
            return '<bililib.User %s [not logged in]>' % self.phone
        else:
            return '<bililib.User %s lv.%d>' % (self.phone, self.level)

    def _requireLogined(func):
        '类中的装饰器，装饰一个，要求调用之前必须登陆'
        @functools.wraps(func)
        def wrapped(self, *args, **kws):
            if not self.logined:
                raise BiliRequireLogin(
                    'This api requires user logined. Call method login() first.')
            return func(self, *args, **kws)

        return wrapped

    # 基础函数

    @staticmethod
    def assertType(item, name, expectedType):
        if not isinstance(item, expectedType):
            raise TypeError('Param %s should be %s, instead of %s.' % (
                name, expectedType.__name__, type(item).__name__
            ))

    @staticmethod
    def _sign(s):
        return hashlib.md5(
            (s + User.SECRET_KEY).encode('utf8')).hexdigest()

    def _getPwd(self, username, password):
        '对密码进行 RSA 加密'
        url = 'https://passport.bilibili.com/api/oauth2/getKey'
        params = {
            'appkey': self.APPKEY,
            'sign': self._sign(f'appkey={self.APPKEY}')
        }

        data = self.do(requests.post, url, params)

        salt, pubKey = data['hash'], data['key']
        key = rsa.PublicKey.load_pkcs1_openssl_pem(pubKey.encode('utf8'))
        password = base64.b64encode(
            rsa.encrypt((salt + password).encode('utf8'), key))
        password = parse.quote_plus(password)
        username = parse.quote_plus(username)
        return username, password

    def login(self):
        '''登陆

        Note:
            用户需要手动调用本方法，在登陆后，user.level, user.coins, user.name 
            会刷新, user.csrf 变为可用。

        '''
        self.logger.debug(f'用户 {self.phone} 登陆中...')

        url = "https://passport.bilibili.com/api/v2/oauth2/login"

        user, pwd = self._getPwd(self.phone, self.password)
        params = f'appkey={self.APPKEY}&password={pwd}&username={user}'
        sign = self._sign(params)
        params += '&sign=' + sign

        data = self.do(requests.post, url, data=params,
                       headers={"Content-type": "application/x-www-form-urlencoded"})

        for cookie in data['cookie_info']['cookies']:
            self.session.cookies[cookie['name']] = cookie['value']
        self.logger.info(f'用户 {self.phone} 登陆成功')
        self.logined = True

        self.getUserInfo()

    def do(self, method, url, *args, times=1, **kws):
        # robust
        if times >= 5:
            raise BiliError('Max retry times reached.')

        try:
            response = method(url, *args, **kws)
        except requests.ConnectTimeout:
            self.logger.warning('%s.do: ConnectTimeout. Retrying...' %
                                type(self).__name__)
            return self.do(method, url, *args, times=times+1, **kws)
        except requests.ConnectionError:
            self.logger.warning('%s.do: ConnectionError. Retrying...' %
                                type(self).__name__)
            return self.do(method, url, *args, times=times+1, **kws)

        try:
            jsData = response.json()
        except json.JSONDecodeError:
            raise RuntimeError(
                'response is not a json string. %s' % response.text)

        if jsData['code']:
            raise BiliError(jsData.get('message', ''))

        return jsData.get('data', None)

    def get(self, url, *args, **kws):
        return self.do(self.session.get, url, *args, **kws)

    def post(self, url, *args, **kws):
        return self.do(self.session.post, url, *args, **kws)

    # 接口

    @_requireLogined
    def getUserInfo(self):
        '''拉取用户的信息

        用来刷新用户信息，一般来说不需要手动调用。

        Raises:
            BiliRequireLogin: 如果用户未调用过 login() 方法
        '''
        url = 'http://account.bilibili.com/home/userInfo'
        data = self.get(url, headers={'Host': 'account.bilibili.com'})
        self.level = data['level_info']['current_level']
        self.coins = data['coins']
        self.name = data['uname']

    @_requireLogined
    def updateCoins(self):
        '''更新硬币数量

        Raises:
            BiliRequireLogin: 如果用户未调用过 login() 方法

        '''
        url = 'https://account.bilibili.com/site/getCoin'
        data = self.get(url, headers={'Host': 'account.bilibili.com',
                                      'Referer': 'https://account.bilibili.com/account/coin'})
        self.coins = data['money']

    @_requireLogined
    def postDanmu(self, danmu):
        '''发送弹幕。

        Args:
            danmu(bililib.Danmu): 要发送的弹幕

        Returns:
            None

        Raises:
            BiliError: if any error occured.
        '''
        import bililib
        self.assertType(danmu, 'danmu', bililib.Danmu)

        url = 'https://api.bilibili.com/x/v2/dm/post'
        param = {
            'type': danmu.mode.value,           # 模式
            'oid': danmu.cid,                   # cid, 可用 self.getCid 获得
            'msg': danmu.msg,                   # 弹幕内容
            'aid': danmu.aid,                   # aid
            'progress': int(danmu.t),           # 时间，毫秒为单位
            'color': int(danmu.color),          # 十六进制的 RGB
            'fontsize': danmu.fontsize,         # 字体大小，两种规格，这个是默认的那个
            'pool': 0,                          # 不知道，猜测是弹幕池，放 0
            'mode': danmu.mode.value,           # mode 和 type 有啥区别？
            'plat': 1,                          # 应该是平台
            'rnd': int(1000000 * time.time()),  # 时间，单位 us
            'csrf': self.csrf                   # csrf 参数
        }
        assert self.csrf != ''
        self.post(url, param)

        self.logger.info(f'弹幕 {danmu} 发送成功')
        return

    @_requireLogined
    def giveCoin(self, aid, num=1):
        '''给视频投硬币。

        Args:
            aid (int): 视频 aid。
            num (int, 1 or 2): 投币数量。

        Raises:
            BiliRequireLogin: 如果未登录。
            TypeError: 如果类型不匹配。
            ValueError: 如果投币数量不是 1 或 2。
            BiliError: 根据 b 站返回确定。
        '''
        self.assertType(aid, 'aid', int)
        self.assertType(num, 'num', int)
        if not num in (1, 2):
            raise ValueError('num should be either 1 or 2, but not %d.' % num)

        url = 'https://api.bilibili.com/x/web-interface/coin/add'
        params = {
            'aid': aid,
            'multiply': num,
            'cross_domain': 'true',
            'csrf': self.csrf
        }

        try:
            data = self.post(url, params, headers={
                'Host': 'api.bilibili.com',
                'Origin': 'https://www.bilibili.com',
                'Referer': 'https://www.bilibili.com/video/av%d' % aid})
            if data is not None:
                raise RuntimeError(
                    'return data is supposed to be None, received %s' % data)
        except BiliError as ex:
            self.logger.error(ex)
            raise

        return data

    # properties

    @property
    @_requireLogined
    def csrf(self):
        return self.session.cookies['bili_jct']

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value):
        self.assertType(value, 'level', int)
        self._level = value

    @property
    def coins(self):
        return self._coins

    @coins.setter
    def coins(self, value):
        self.assertType(value, 'coins', int)
        self._coins = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self.assertType(value, 'name', str)
        self._name = value
