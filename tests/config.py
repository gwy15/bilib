import json
import os


def getConfig():
    configFile = os.path.dirname(__file__) + os.sep + 'test_config.json'
    if not os.path.exists(configFile):
        raise RuntimeError('测试用配置文件未找到')
    with open(configFile) as f:
        result = json.load(f)

    userFile = os.path.dirname(__file__) + os.sep + 'user_account.json'
    if os.path.exists(userFile):
        with open(userFile) as f:
            result.update(json.load(f))
    else:
        for key in ('phone', 'username', 'password'):
            if not key in os.environ:
                raise RuntimeError('未找到环境变量 %s' % key)
            result[key] = os.environ[key]

    return result
