import unittest
import tempfile
import yaml
import os
from work.exargs import ConfigResolver

class TestConfigResolver(unittest.TestCase):

    def _write_temp_yaml(self, data: dict) -> str:
        tmp = tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False)
        yaml.dump(data, tmp)
        tmp.close()
        self.addCleanup(lambda: os.remove(tmp.name))
        return tmp.name

    def test_no_variable(self):
        config = {"a": 123, "b": {"c": "hello"}}
        path = self._write_temp_yaml(config)
        resolved = ConfigResolver(path).parse()
        self.assertEqual(resolved["a"], 123)
        self.assertEqual(resolved["b"]["c"], "hello")

    def test_single_variable(self):
        config = {
            "base": {"dir": "/data"},
            "path": "${base.dir}/file.txt"
        }
        path = self._write_temp_yaml(config)
        resolved = ConfigResolver(path).parse()
        self.assertEqual(resolved["path"], "/data/file.txt")

    def test_nested_variable(self):
        config = {
            "base": {"dir": "/root"},
            "log": {
                "dir": "${base.dir}/log",
                "file": "${log.dir}/run.log"
            }
        }
        path = self._write_temp_yaml(config)
        resolved = ConfigResolver(path).parse()
        self.assertEqual(resolved["log"]["file"], "/root/log/run.log")

    def test_cross_level_dependency(self):
        config = {
            "a": {"x": "val"},
            "b": {"y": "${a.x}"}
        }
        path = self._write_temp_yaml(config)
        resolved = ConfigResolver(path).parse()
        self.assertEqual(resolved["b"]["y"], "val")

    def test_multi_level_chain(self):
        config = {
            "a": "base",
            "b": "${a}/dir",
            "c": "${b}/file.txt"
        }
        path = self._write_temp_yaml(config)
        resolved = ConfigResolver(path).parse()
        self.assertEqual(resolved["c"], "base/dir/file.txt")

    def test_cycle_detection(self):
        config = {
            "a": "${b}",
            "b": "${c}",
            "c": "${a}"
        }
        path = self._write_temp_yaml(config)
        with self.assertRaises(ValueError) as context:
            ConfigResolver(path).parse()
        self.assertIn("Cycle(s) detected", str(context.exception))

    def test_empty_variable_value(self):
        config = {
            "x": "",
            "y": "${x}"
        }
        path = self._write_temp_yaml(config)
        resolved = ConfigResolver(path).parse()
        self.assertEqual(resolved["y"], "")

if __name__ == '__main__':
    unittest.main()
