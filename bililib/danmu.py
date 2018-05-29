import requests
from enum import Enum
import logging
import unittest


logger = logging.getLogger(__name__)


class DanmuMode(Enum):
    '弹幕的类型，FLY 平飞, DOWN 底部弹幕，TOP 顶部弹幕'
    FLY = 1
    DOWN = 4
    TOP = 5


class Danmu:
    '弹幕类。在初始化时会自动查找 cid。'

    def __init__(self, msg, t, aid, cid=None, fontsize=25, color=0xFFFFFF, mode=DanmuMode.FLY):
        self.msg = msg
        self.t = t
        self.aid = aid
        self.fontsize = fontsize
        self.color = color
        self.mode = mode

        self.cid = cid if cid else self.getCid(aid)

    @staticmethod
    def getCid(aid):
        logging.debug('获取 cid 中')
        url = f'https://www.bilibili.com/widget/getPageList?aid={aid}'
        data = requests.get(url).json()
        if len(data) != 1:
            logging.warning(f'当前 aid {aid} 有多 P，建议手动指定 aid')
        cid = data[0]['cid']
        logging.debug(f'cid 获取: {cid}')
        return cid

    def getTimeStr(self):
        t = self.t
        # ms
        res = '.%03d' % (t % 1000)
        t //= 1000

        # s, min
        for _ in range(2):
            res = ('%d' if t < 60 else ':%02d') % (t % 60) + res
            t //= 60
            if t == 0:
                return res

        res = '%d' % t + res
        return res

    def __repr__(self):
        return f'<Danmu "{self.msg}" @{self.getTimeStr()} #{self.aid}>'
