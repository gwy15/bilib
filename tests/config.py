import json
import os


def getConfig():
    configFile = os.path.dirname(__file__) + os.sep + 'test_config.json'
    if not os.path.exists(configFile):
        raise RuntimeError('测试用配置文件未找到')
    with open(configFile) as f:
        return json.load(f)
