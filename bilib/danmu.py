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
    '''弹幕类。

    Args:
        msg (str): 要发送的弹幕内容。
        t (int or float): 弹幕在视频中的时间轴，以 ms 为单位。
        aid (int): 视频的 aid，即 www.bilibili.com/video/av{aid}。
        cid (int): 视频分 P 的 cid。如果不给定，将在构造函数中自动查找。
        fontsize (int): 弹幕字号，默认 25，不建议改动。
        color (int): 弹幕的颜色，默认白色。以 16 进制（web 形式）计算。
        mode (bilib.DanmuMode): 弹幕模式，默认平飞。
    '''

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
        '''获取 aid 对应的 cid。

        Note:
            取第一 P 的 cid，如果是多 P，建议手动指定。

        '''
        logger.debug('获取 cid 中')
        url = f'https://www.bilibili.com/widget/getPageList?aid={aid}'
        data = requests.get(url).json()
        if len(data) != 1:
            logger.warning(f'当前 aid {aid} 有多 P，建议手动指定 aid')
        cid = data[0]['cid']
        logger.debug(f'cid 获取: {cid}')
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
