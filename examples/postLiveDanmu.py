import random
import json

import bilib


def postLiveDanmu(users, roomid, msg):
    while True:
        user = random.choice(users)
        if not user.logined:
            user.login()
        try:
            user.postLiveDanmu(msg, roomid)
            break
        except bilib.user.BiliError as ex:
            if ex.code == -403:
                users.remove(user)
                print(f'{user}: {ex}。剩余用户：{len(users)}个')
            else:
                raise


def main():
    with open('users.json') as f:
        USER_INFOS = json.load(f)

    cid, title = bilib.User.getRoomInfo(input('输入房间 ID: ')).values()
    uname = bilib.User.getAncherName(cid)
    print('进入 %s 房间: %s' % (uname, title))

    users = [bilib.User(*info) for info in USER_INFOS]

    while True:
        msg = input('> ')
        msg = msg.replace('\\n', '\n')
        if msg in ('q', 'quit'):
            break
        elif len(msg) > 20:
            print('文本过长')
        else:
            postLiveDanmu(users, cid, msg)


if __name__ == '__main__':
    main()
