import logging
import hashlib
import base64
import time
from urllib import parse
import json
import re
import functools
import unittest

import requests
import rsa


class BiliError(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code

    def __repr__(self):
        return '<%s%s: %s>' % (
            type(self).__name__,
            (' (%d)' % self.code) if self.code else '',
            str(self))


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

    def __init__(self, phone, password, username=None, level=0, coins=0, **kws):
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
            return '<%s %s [not logged in]>' % (type(self).__name__, self.phone)
        else:
            return '<%s %s lv.%d>' % (type(self).__name__, self.phone, self.level)

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
    def _flaten(params):
        return '&'.join('%s=%s' % item for item in sorted(
            params.items(), key=lambda item: item[0]
        ))

    @staticmethod
    def _signed(params, key=None):
        if key is None:
            key = User.SECRET_KEY

        s = User._flaten(params)
        params['sign'] = hashlib.md5(
            (s + key).encode('utf8')).hexdigest()
        return params

    def _getPwd(self, username, password):
        '对密码进行 RSA 加密'
        url = 'https://passport.bilibili.com/api/oauth2/getKey'
        params = self._signed({'appkey': self.APPKEY})

        data = self.do(requests.post, url, params)

        salt, pubKey = data['hash'], data['key']
        key = rsa.PublicKey.load_pkcs1_openssl_pem(pubKey.encode('utf8'))
        password = base64.b64encode(
            rsa.encrypt((salt + password).encode('utf8'), key))
        password = parse.quote_plus(password)
        username = parse.quote_plus(username)
        return username, password

    def do(self, method, url, *args, times=1, **kws):
        # robust
        if times >= 5:
            raise BiliError('Max retry times reached.')

        # 处理 requests 抛出的异常
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

        # 处理 API error
        if response.text == 'Fatal: API error':
            raise BiliError(response.text)

        # 处理 json 无法解析
        try:
            jsData = response.json()
        except json.JSONDecodeError:
            raise RuntimeError(
                'Response is not a json string. %s' % response.text)

        # 处理错误返回码
        if jsData['code'] not in (0, 'REPONSE_OK'):
            raise BiliError(jsData.get('message', ''), code=jsData['code'])

        # 返回正常数据
        return jsData.get('data', None)

    def get(self, url, *args, **kws):
        return self.do(self.session.get, url, *args, **kws)

    def post(self, url, *args, **kws):
        return self.do(self.session.post, url, *args, **kws)

    # 登陆部分

    def login(self):
        '''登陆

        Note:
            用户需要手动调用本方法，在登陆后，user.level, user.coins, user.name
            会刷新, user.csrf 变为可用。

        '''
        self.logger.debug(f'用户 {self.phone} 登陆中...')

        url = 'https://passport.bilibili.com/api/v2/oauth2/login'

        user, pwd = self._getPwd(self.phone, self.password)
        params = self._signed({
            'appkey': self.APPKEY,
            'password': pwd,
            'username': user
        })

        data = self.do(requests.post, url,
                       #    params=params,
                       data=self._flaten(params),
                       headers={"Content-type": "application/x-www-form-urlencoded"})

        # 处理返回数据
        self.mid = data['token_info']['mid']
        self._accessToken = data['token_info']['access_token']
        self._refreshToken = data['token_info']['refresh_token']
        self.expiresTime = time.time() + data['token_info']['expires_in']

        for cookie in data['cookie_info']['cookies']:
            self.session.cookies[cookie['name']] = cookie['value']
        self.logger.info(f'用户 {self.phone} 登陆成功')
        self.logined = True

        self.getUserInfo()

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
            danmu(bilib.Danmu): 要发送的弹幕

        Returns:
            None

        Raises:
            BiliError: if any error occured.
        '''
        import bilib
        self.assertType(danmu, 'danmu', bilib.Danmu)

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

        data = self.post(url, params, headers={
            'Host': 'api.bilibili.com',
            'Origin': 'https://www.bilibili.com',
            'Referer': 'https://www.bilibili.com/video/av%d' % aid})
        if data is not None:
            raise BiliError(
                'return data is supposed to be None, received %s' % data)

        return data

    # 弹幕

    # 直播
    @staticmethod
    def getRoomCid(showID):
        url = 'https://live.bilibili.com/%s' % showID
        page = requests.get(url).content.decode('utf8')
        results = re.findall(r'"room_id":(\d+)', page)
        assert all(item == results[0] for item in results)
        return results[0]

    @_requireLogined
    def getUserLiveLevel(self):
        data = self.get('https://api.live.bilibili.com/User/getUserInfo?ts=%s' %
                        int(1000 * time.time()),
                        headers={
                            'Host': 'api.live.bilibili.com'
                        })
        return data['user_level']

    @_requireLogined
    def postLiveDanmu(self, msg, roomid):
        url = 'https://api.live.bilibili.com/msg/send'
        form = {
            'color': 0xFFFFFF,
            'fontsize': 25,
            'mode': 1,
            'msg': msg,
            'rnd': int(time.time()),
            'roomid': roomid,
            'csrf_token': self.csrf
        }
        headers = {
            'Host': 'api.live.bilibili.com'
        }
        res = self.post(url, form, headers=headers)
        if res != []:
            raise BiliError('result: %s' % res)

    @_requireLogined
    def comment(self, aid, msg):
        '''评论视频。

        Args:
            aid (int): 视频 aid。
            msg (str): 评论内容。

        Raises:
            BiliRequireLogin: 如果未登录。
            TypeError: 如果类型不匹配。
            BiliError: 根据 b 站返回确定。
        '''
        self.assertType(aid, 'aid', int)
        self.assertType(msg, 'msg', str)

        url = 'https://api.bilibili.com/x/v2/reply/add'
        params = {
            'oid': aid,
            'type': '1',
            'message': msg,
            'plat': 1,
            'jsonp': 'jsonp',
            'csrf': self.csrf
        }

        data = self.post(url, params=params)
        return data

    # 密保问题

    @_requireLogined
    def hasSafeQuestion(self):
        '''检查用户是否有安全问题

        return:
            bool
        '''
        url = 'https://account.bilibili.com/home/reward'
        data = self.get(url, headers={
            'Referer': 'https://account.bilibili.com/account/home',
            'Host': 'account.bilibili.com'})
        return data['safequestion']

    @_requireLogined
    def initSafeQuestion(self, questionID, answer):
        '''初始化密保问题

        Args:
            questionID (int): 安全问题编号
            answer (str): 密保问题答案
        '''
        self.assertType(questionID, 'questionID', int)
        self.assertType(answer, 'answer', str)

        return self._updateSafeQuestion(
            questionID, answer,
            0, '', 1)

    @_requireLogined
    def verifySafeQuestion(self, questionID, answer):
        '''验证密保问题

        Args:
            questionID (int): 安全问题编号
            answer (str): 密保问题答案

        return:
            bool: True if correct, False otherwise
        '''
        self.assertType(questionID, 'questionID', int)
        self.assertType(answer, 'answer', str)
        try:
            self._updateSafeQuestion(
                questionID, answer,
                0, '', 1)
            return True
        except BiliError as ex:
            if ex.code == -632:
                return False
            else:
                raise

    @_requireLogined
    def changeSafeQuestion(self, oldQuestionID, oldAnswer, newQuestionID, newAnswer):
        '''更改密保问题

        Args:
            oldQuestionID (int): 旧密保问题编号
            oldAnswer (str): 旧密保问题答案
            newQuestionID (int): 新密保问题编号
            newAnswer (str): 新密保问题答案

        Raise:
            BiliError: 验证未通过
        '''
        self.assertType(oldQuestionID, 'oldQuestionID', int)
        self.assertType(oldAnswer, 'oldAnswer', str)
        self.assertType(newQuestionID, 'newQuestionID', int)
        self.assertType(newAnswer, 'newAnswer', str)

        self._updateSafeQuestion(
            oldQuestionID, oldAnswer,
            newQuestionID, newAnswer, 1)
        self._updateSafeQuestion(
            oldQuestionID, oldAnswer,
            newQuestionID, newAnswer, 2)

    @_requireLogined
    def _updateSafeQuestion(self, oldSQ, oldAnswer, newSQ, newAnswer, canChange):
        url = 'https://passport.bilibili.com/web/site/updateSafeQuestion'
        params = {
            'old_safe_question': oldSQ,
            'old_answer': oldAnswer,
            'new_safe_question': newSQ,
            'new_answer': newAnswer,
            'can_change_safe_qa': canChange,
            'csrf': self.csrf
        }
        data = self.post(url, params, headers={
            'Host': 'passport.bilibili.com'})
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
