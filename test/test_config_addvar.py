import unittest
import tempfile
import yaml
import os
from work.exargs import ConfigResolver

class TestConfigResolverAddVariable(unittest.TestCase):
    def _write_temp_yaml(self, content: dict) -> str:
        fd, path = tempfile.mkstemp(suffix=".yaml")
        with os.fdopen(fd, 'w') as f:
            yaml.dump(content, f)
        return path

    def test_add_variable_literal(self):
        config = {
            'base': {'dir': '/opt'}
        }
        path = self._write_temp_yaml(config)
        resolver = ConfigResolver(path)
        resolver.add_variable('new.value', '12345')
        resolved = resolver.resolved
        self.assertEqual(resolved['new.value'], '12345')

    def test_add_variable_with_reference(self):
        config = {
            'base': {'dir': '/home/user'}
        }
        path = self._write_temp_yaml(config)
        resolver = ConfigResolver(path)
        resolved = resolver.add_variable('log.path', '${base.dir}/log')
        self.assertEqual(resolved['log']['path'], '/home/user/log')

    def test_add_variable_overwrite(self):
        config = {
            'base': {'dir': '/old/path'}
        }
        path = self._write_temp_yaml(config)
        resolver = ConfigResolver(path)
        resolver.add_variable('base.dir', '/new/path')
        resolved = resolver.resolved
        self.assertEqual(resolved['base.dir'], '/new/path')

    def test_add_variable_indirect_dependency(self):
        config = {
            'a': 'hello'
        }
        path = self._write_temp_yaml(config)
        resolver = ConfigResolver(path)
        resolver.add_variable('b', '${a} world')
        resolver.add_variable('c', '${b}!')
        resolved = resolver.resolved
        self.assertEqual(resolved['c'], 'hello world!')