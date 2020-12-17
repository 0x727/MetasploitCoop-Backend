# payload 插件必须属性
REQUIRED_ATTRS = [
    'NAME',  # 插件名称
    'DESC',  # 插件描述
    'run',   # 插件生成payload方法
]
# payload 插件可选属性
OPTIONAL_ATTRS = [
    'OPTIONS',    # payload插件选项
    'REFERENCES', # payload插件引用资料
    'ATTCK',      # payload插件所涉及到的ATT&CK向量
    'AUTHOR',     # payload插件作者
]