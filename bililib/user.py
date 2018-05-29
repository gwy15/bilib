import logging
import hashlib
import base64
import time
from urllib import parse
import functools
import unittest

import requests
import rsa

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BiliError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg

    def __repr__(self):
        return '%s: %s' % (type(self).__name__, self.msg)


class BiliRequireLogin(BiliError):
    pass


def requireLogined(func):
    @functools.wraps(func)
    def newfunc(self, *args, **kws):
        if not self.logined:
            raise BiliRequireLogin(
                'This api requires user logined. Call method login() first.')
        return func(self, *args, **kws)
    return newfunc


class User:
    '''bilibili 用户基类\n
    实现登陆、发送弹幕
    '''
    APPKEY = '1d8b6e7d45233436'
    SECRET_KEY = "560c52ccd288fed045859ed18bffd973"

    def __init__(self, username, password):
        self.session = requests.session()
        self.username = username
        self.password = password
        self.csrf = ''

        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
        self.session.headers['Host'] = 'api.bilibili.com'
        self.session.headers['Origin'] = 'https://www.bilibili.com'
        self.session.headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        self.logined = False

    def __del__(self):
        self.session.close()

    @staticmethod
    def sign(s):
        return hashlib.md5(
            (s + User.SECRET_KEY).encode('utf8')).hexdigest()

    def getPwd(self, username, password):
        '对密码进行 RSA 加密'
        url = 'https://passport.bilibili.com/api/oauth2/getKey'
        params = {
            'appkey': self.APPKEY,
            'sign': self.sign(f'appkey={self.APPKEY}')
        }
        js = requests.post(url, data=params).json()

        if js['code'] != 0:
            raise RuntimeError('getKey: %s' % js['message'])
        data = js['data']
        salt, pubKey = data['hash'], data['key']
        key = rsa.PublicKey.load_pkcs1_openssl_pem(pubKey.encode('utf8'))
        password = base64.b64encode(
            rsa.encrypt((salt + password).encode('utf8'), key))
        password = parse.quote_plus(password)
        username = parse.quote_plus(username)
        return username, password

    def login(self):
        '登陆'
        logging.info(f'用户 {self.username} 登陆中...')

        url = "https://passport.bilibili.com/api/v2/oauth2/login"

        user, pwd = self.getPwd(self.username, self.password)
        params = f'appkey={self.APPKEY}&password={pwd}&username={user}'
        sign = self.sign(params)
        params += '&sign=' + sign

        js = requests.post(url, data=params,
                           headers={"Content-type": "application/x-www-form-urlencoded"}).json()
        if js['code'] != 0:
            raise RuntimeError('login: %s' % js['message'])

        for cookie in js['data']['cookie_info']['cookies']:
            self.session.cookies[cookie['name']] = cookie['value']
        self.csrf = self.session.cookies['bili_jct']
        logging.info(f'用户 {self.username} 登陆成功')
        self.logined = True

        self.getUserInfo()

    @staticmethod
    def do(method, url, *args, **kws):
        jsData = method(url, *args, **kws).json()
        if jsData['code']:
            raise BiliError(jsData.get('message', ''))

        return jsData['data']

    def get(self, url, *args, **kws):
        return self.do(self.session.get, url, *args, **kws)

    def post(self, url, *args, **kws):
        return self.do(self.session.post, url, *args, **kws)

    @requireLogined
    def postDanmu(self, danmu):
        '''
        发送弹幕
        danmu: danmu.Danmu
        '''
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

        logging.info(f'弹幕 {danmu} 发送成功')
        return

    @requireLogined
    def getUserInfo(self):
        'return None'
        url = 'http://account.bilibili.com/home/userInfo'
        data = self.get(url, headers={'Host': 'account.bilibili.com'})
        self.level = data['level_info']['current_level']
        self.coins = data['coins']
        self.name = data['uname']
