You can install this package by
```bash
pip install --no-cache-dir -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple exargs-qiaoy
```

And here is an example for use
```python
from exargs import ConfigResolver
config_path = './config.yaml‘
config = ConfigResolver(config_path).parse()
print(config['data_dir'])
print(config['path']['input_path'])
config.add_variable('base.dir', '/new/path')
print(config['base.dir'])
print(config['base']['dir'])
```
with the config file:
```yaml
#./config.yaml
data_dir: "/home/user/data"
model_name: "resnet50"
train_file: "${data_dir}/train.json"
val_file: "${data_dir}/val.json"
path: {
    input_path: "${data_dir}/input",
    output_path: "${data_dir}/output"
}
```