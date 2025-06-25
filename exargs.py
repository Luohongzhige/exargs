import os
import re
import yaml
import json
from collections import defaultdict
from typing import Any

class ConfigResolver:
    VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.raw_config = self._load_config()
        self.flat_config = self._flatten(self.raw_config)
        self.dependencies = self._extract_dependencies()
        self.resolved = None

    def parse(self):
        order = self._topo_sort_with_cycle_check()
        resolved = {}
        for key in order:
            value = self.flat_config[key]
            resolved[key] = self._resolve_value_recursively(value, resolved)
        self.resolved = resolved
        return self._unflatten(resolved)

    def _resolve_value_recursively(self, value, resolved):
        previous_value = None
        while isinstance(value, str) and self.VAR_PATTERN.search(value):
            if value == previous_value:
                raise ValueError(f"Unresolved variables remain in value: {value}")
            previous_value = value
            matches = self.VAR_PATTERN.findall(value)
            for var in matches:
                if var in resolved:
                    var_value = resolved[var]
                elif var in self.flat_config:
                    var_value = self._resolve_value_recursively(self.flat_config[var], resolved)
                    resolved[var] = var_value
                else:
                    raise ValueError(f"Unresolved variable: {var}")
                value = value.replace(f"${{{var}}}", str(var_value))
        return value

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
        flat_keys = set(self.flat_config.keys())
        for key, value in self.flat_config.items():
            if isinstance(value, str):
                for var in self.VAR_PATTERN.findall(value):
                    if var != key:
                        deps[key].add(var)
        for key in self.flat_config:
            deps.setdefault(key, set())
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
            for neighbor in self.dependencies[node]:
                dfs(neighbor, path + [node])
            visited[node] = 2
            order.append(node)

        for key in self.dependencies:
            if visited.get(key, 0) == 0:
                dfs(key, [])

        if has_cycle:
            cycles = [" -> ".join(c) for c in has_cycle]
            raise ValueError("Cycle(s) detected in variable references:\n" + "\n".join(cycles))

        return order[::-1]

    def add_variable(self, key: str, value: Any):
        """
        动态添加或覆盖变量，并更新依赖图结构，自动重新解析。
        添加的值可以引用已有变量。
        """
        if not isinstance(key, str):
            raise TypeError("Key must be a string")
        self.flat_config[key] = value
        self.dependencies = self._extract_dependencies()
        return self.parse()
