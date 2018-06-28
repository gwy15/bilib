# bilib
[![build_status](https://travis-ci.org/gwy15/bilib.svg?branch=master)](https://travis-ci.org/gwy15/bilib/)

哔哩哔哩的一些 API 实现。

目前实现的有：
+ 登陆
+ 查询用户信息（等级、硬币、用户名）
+ 发送弹幕
+ 投币
+ 评论视频
+ 用户密保问题初始化和修改

继承 User 类以加入新的接口。

因为采用了新的写法，**只支持 Python 3.6.**

## Install
    $ pip install -r requirements.txt
    $ py setup.py install

## Usage
    from bilib import User, Danmu

    user = User(username, password)
    user.login()
    danmu = Danmu(msg, timeInMs, aid)
    user.postDanmu(danmu)
