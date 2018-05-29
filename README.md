# bililib
[![build_status](https://travis-ci.org/gwy15/bililib.svg?branch=master)](https://travis-ci.org/gwy15/bililib/)


login in and post danmu!

Notice that this code only supports Python 3.6.

## Install

    py setup.py install

## Usage

    from bililib import User, Danmu

    user = User(username, password)
    user.login()
    danmu = Danmu(msg, timeInMs, aid)
    user.postDanmu(danmu)