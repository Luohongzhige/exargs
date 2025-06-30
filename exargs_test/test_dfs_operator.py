import unittest
import tempfile
import os
import yaml
from exargs import ConfigResolver   # 修改为你的包导入路径


class TestAttrExpression(unittest.TestCase):
    """专门验证点属性表达式解析功能"""

    # ----------- 工具函数 -----------
    def _tmp_yaml(self, content: dict):
        fp = tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False)
        yaml.dump(content, fp)
        fp.flush()
        return fp.name

    def tearDown(self):
        # 清理临时 YAML
        for f in os.listdir(tempfile.gettempdir()):
            if f.endswith(".yaml"):
                try:
                    os.unlink(os.path.join(tempfile.gettempdir(), f))
                except:
                    pass

    # ----------- 测试用例 -----------
    def test_bool_and_dotted_attr(self):
        cfg = {
            "cache": {
                "all": False,
                "roadnet_all": "${{ True && cache.all }}"
            }
        }
        path = self._tmp_yaml(cfg)
        res = ConfigResolver(path).parse()
        self.assertEqual(res["cache"]["roadnet_all"], "False")  # 解析为字符串 "False"

    def test_nested_attr_chain(self):
        cfg = {
            "deep": {
                "inner": {
                    "flag": True
                }
            },
            "use_flag": "${{ deep.inner.flag }}"
        }
        path = self._tmp_yaml(cfg)
        res = ConfigResolver(path).parse()
        self.assertEqual(res["use_flag"], "True")

    def test_attr_arithmetic_mix(self):
        cfg = {
            "base": {"num": 10},
            "inc": {"val": 7},
            "sum": "${{ base.num + inc.val }}"
        }
        path = self._tmp_yaml(cfg)
        res = ConfigResolver(path).parse()
        self.assertEqual(res["sum"], "17")


if __name__ == "__main__":
    unittest.main()
