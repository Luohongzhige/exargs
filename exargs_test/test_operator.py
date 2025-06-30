import unittest
import tempfile
import os
import yaml
from exargs import ConfigResolver


class TestConfigResolver(unittest.TestCase):

    def _write_temp_config(self, content: dict, suffix='.yaml'):
        tmp = tempfile.NamedTemporaryFile(mode='w+', suffix=suffix, delete=False)
        yaml.dump(content, tmp)
        tmp.flush()
        return tmp.name

    def test_basic_variable_substitution(self):
        config = {'a': 5, 'b': '${a}'}
        path = self._write_temp_config(config)
        resolver = ConfigResolver(path)
        result = resolver.parse()
        self.assertEqual(result['b'], '5')

    def test_expression_evaluation_add_mul(self):
        config = {'a': 2, 'b': 3, 'c': '${{ a + b }}', 'd': '${{ a * b }}'}
        path = self._write_temp_config(config)
        resolver = ConfigResolver(path)
        result = resolver.parse()
        self.assertEqual(result['c'], '5')
        self.assertEqual(result['d'], '6')

    def test_expression_logic(self):
        config = {'x': 1, 'y': 2, 'expr': '${{ x < 2 && y > 1 }}'}
        path = self._write_temp_config(config)
        resolver = ConfigResolver(path)
        result = resolver.parse()
        self.assertEqual(result['expr'], 'True')

    def test_expression_max_min(self):
        config = {'a': 10, 'b': 20, 'c': '${{ max(a, b - 5) }}'}
        path = self._write_temp_config(config)
        resolver = ConfigResolver(path)
        result = resolver.parse()
        self.assertEqual(result['c'], '15')

    def test_nested_variables_and_expression(self):
        config = {
            'x': 10,
            'y': '${x}',
            'z': '${{ int(y) + 5 }}'
        }
        path = self._write_temp_config(config)
        resolver = ConfigResolver(path)
        result = resolver.parse()
        self.assertEqual(result['z'], '15')

    def test_env_variable_substitution(self):
        os.environ['MY_VAR'] = 'env_value'
        config = {'a': '${MY_VAR}'}
        path = self._write_temp_config(config)
        resolver = ConfigResolver(path)
        result = resolver.parse()
        self.assertEqual(result['a'], 'env_value')

    def test_list_and_dict_support(self):
        config = {
            'a': 2,
            'b': [1, '${a}', '${{ a * 3 }}'],
            'c': {'inner': '${{ a + 1 }}'}
        }
        path = self._write_temp_config(config)
        resolver = ConfigResolver(path)
        result = resolver.parse()
        self.assertEqual(result['b'], [1, '2', '6'])
        self.assertEqual(result['c']['inner'], '3')

    def test_cycle_detection(self):
        config = {'a': '${b}', 'b': '${c}', 'c': '${a}'}
        path = self._write_temp_config(config)
        resolver = ConfigResolver(path)
        with self.assertRaises(ValueError) as ctx:
            resolver.parse()
        self.assertIn('Cycle(s) detected', str(ctx.exception))

    def test_add_variable_dynamic(self):
        config = {'a': 1}
        path = self._write_temp_config(config)
        resolver = ConfigResolver(path)
        resolver.parse()
        new_result = resolver.add_variable('b', '${{ a + 2 }}')
        self.assertEqual(new_result['b'], '3')

    def tearDown(self):
        # 清理所有临时 yaml 文件
        for f in os.listdir(tempfile.gettempdir()):
            if f.endswith(".yaml") or f.endswith(".yml"):
                try:
                    os.remove(os.path.join(tempfile.gettempdir(), f))
                except:
                    pass


if __name__ == '__main__':
    unittest.main()
