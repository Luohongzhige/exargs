import os
import re
import yaml
import json
import ast
import operator as op
from collections import defaultdict
from typing import Any

# 安全运算符和函数
SAFE_OPERATORS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.Mod: op.mod, ast.Pow: op.pow,
    ast.BitXor: op.xor, ast.And: lambda a, b: a and b, ast.Or: lambda a, b: a or b,
    ast.Eq: op.eq, ast.NotEq: op.ne, ast.Lt: op.lt, ast.LtE: op.le,
    ast.Gt: op.gt, ast.GtE: op.ge,
    ast.USub: op.neg, ast.Not: op.not_,
}
SAFE_FUNCTIONS = {
    'min': min, 'max': max, 'abs': abs, 'int': int, 'float': float, 'bool': bool
}

def _preprocess_expr(expr: str) -> str:
    """将表达式中的“&&/||/^”转为 Python 可识别形式。"""
    expr = expr.strip()
    expr = re.sub(r"&&", " and ", expr)
    expr = re.sub(r"\|\|", " or ", expr)
    # 逻辑异或：使用"^"保留为按位异或 (int/bool 都适用)
    return expr

def _eval_expr(expr: str, local_vars: dict):
    expr = _preprocess_expr(expr)

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in local_vars:
                return local_vars[node.id]
            if node.id in os.environ:
                return os.environ[node.id]
            raise KeyError(f"{node.id}")
        elif isinstance(node, ast.BinOp):
            return SAFE_OPERATORS[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return SAFE_OPERATORS[type(node.op)](_eval(node.operand))
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(_eval(v) for v in node.values)
            elif isinstance(node.op, ast.Or):
                return any(_eval(v) for v in node.values)
        elif isinstance(node, ast.Compare):
            left = _eval(node.left)
            for op_, right_ in zip(node.ops, node.comparators):
                if not SAFE_OPERATORS[type(op_)](left, _eval(right_)):
                    return False
                left = _eval(right_)
            return True
        elif isinstance(node, ast.Call):
            func_name = node.func.id
            if func_name not in SAFE_FUNCTIONS:
                raise ValueError(f"Function '{func_name}' not allowed in expressions")
            func = SAFE_FUNCTIONS[func_name]
            args = [_eval(arg) for arg in node.args]
            return func(*args)
        else:
            raise ValueError(f"Unsupported expression: {ast.dump(node)}")

    try:
        tree = ast.parse(expr, mode='eval')
        return _eval(tree)
    except Exception as e:
        raise ValueError(f"Error evaluating expression '{expr}': {e}")


class ConfigResolver:
    VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")
    EXPR_PATTERN = re.compile(r"\$\{\{([^}]+)\}\}")

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.raw_config = self._load_config()
        self.flat_config = self._flatten(self.raw_config)
        self.dependencies = self._extract_dependencies()
        self.resolved = None

    def parse(self):
        order = self._topo_sort_with_cycle_check()
        # 确保所有 flat_config 的 key 都在顺序中（即便没有依赖）
        for key in self.flat_config:
            if key not in order:
                order.append(key)

        resolved = {}
        for key in order:
            if key not in self.flat_config:
                # 仅在 flat_config 不存在时跳过（可能是纯引用变量，比如环境变量）
                continue
            value = self.flat_config[key]
            resolved[key] = self._resolve_value_recursively(value, resolved)

        self.resolved = resolved
        return self._unflatten(resolved)

    def _resolve_value_recursively(self, value, resolved):
        if isinstance(value, list):
            return [self._resolve_value_recursively(v, resolved) for v in value]
        if isinstance(value, dict):
            return {k: self._resolve_value_recursively(v, resolved) for k, v in value.items()}

        # 表达式求值
        if isinstance(value, str) and self.EXPR_PATTERN.search(value):
            def repl_expr(match):
                expr = match.group(1)
                return str(_eval_expr(expr, resolved))
            value = self.EXPR_PATTERN.sub(repl_expr, value)
            return value

        # 变量替换
        previous_value = None
        while isinstance(value, str) and self.VAR_PATTERN.search(value):
            if value == previous_value:
                raise ValueError(f"Unresolved variables remain in value: {value}")
            previous_value = value
            for var in self.VAR_PATTERN.findall(value):
                if var in resolved:
                    var_value = resolved[var]
                elif var in self.flat_config:
                    var_value = self._resolve_value_recursively(self.flat_config[var], resolved)
                    resolved[var] = var_value
                elif var in os.environ:
                    var_value = os.environ[var]
                else:
                    raise ValueError(f"Unresolved variable: {var}")
                value = value.replace(f"${{{var}}}", str(var_value))
        return value

    # ----------------------------- 工具函数 -----------------------------
    def _load_config(self):
        with open(self.config_path, 'r') as f:
            if self.config_path.endswith(('.yaml', '.yml')):
                return yaml.safe_load(f)
            elif self.config_path.endswith('.json'):
                return json.load(f)
            else:
                raise ValueError("Only .yaml, .yml, or .json files are supported.")

    def _flatten(self, d, parent_key='', sep='.'):
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(self._flatten(v, new_key, sep))
            else:
                items[new_key] = v
        return items

    def _unflatten(self, d, sep='.'):
        result = {}
        for k, v in d.items():
            keys = k.split(sep)
            target = result
            for key in keys[:-1]:
                target = target.setdefault(key, {})
            target[keys[-1]] = v
        return result

    def _extract_dependencies(self):
        deps = defaultdict(set)

        for key, value in self.flat_config.items():
            if isinstance(value, str):
                deps[key].update(self.VAR_PATTERN.findall(value))
                for expr in self.EXPR_PATTERN.findall(value):
                    vars_in_expr = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", expr)
                    deps[key].update(vars_in_expr)

        # 确保所有被引用的变量都在图中
        all_nodes = set(deps.keys()).union(*deps.values()) if deps else set()
        for node in all_nodes:
            deps.setdefault(node, set())

        return deps

    def _topo_sort_with_cycle_check(self):
        visited = {}
        order = []
        has_cycle = []

        def dfs(node, path):
            if visited.get(node, 0) == 1:
                has_cycle.append(path + [node])
                return
            if visited.get(node, 0) == 2:
                return
            visited[node] = 1
            for neighbor in self.dependencies.get(node, []):
                dfs(neighbor, path + [node])
            visited[node] = 2
            order.append(node)

        for key in sorted(self.dependencies):
            if visited.get(key, 0) == 0:
                dfs(key, [])

        if has_cycle:
            cycles = [" -> ".join(c) for c in has_cycle]
            raise ValueError("Cycle(s) detected in variable references:\n" + "\n".join(cycles))

        # 不再 reverse，保持依赖先解析
        return order

    def add_variable(self, key: str, value: Any):
        if not isinstance(key, str):
            raise TypeError("Key must be a string")
        self.flat_config[key] = value
        self.dependencies = self._extract_dependencies()
        return self.parse()
