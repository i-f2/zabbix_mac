#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动合并 YAML 内容
"""

import yaml
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('manual_yaml_merge')

def normalize_keys(data):
    """标准化键名，使用 snake_case"""
    if isinstance(data, dict):
        normalized = {}
        for key, value in data.items():
            # 转换为 snake_case
            snake_key = key.lower().replace(' ', '_')
            normalized[snake_key] = normalize_keys(value)
        return normalized
    elif isinstance(data, list):
        return [normalize_keys(item) for item in data]
    else:
        return data

def add_comments(yaml_content):
    """为核心配置添加中文注释"""
    # 这里可以根据需要添加注释
    # 由于 YAML 本身不支持内联注释，我们将在生成 YAML 时添加注释
    return yaml_content

def generate_yaml(yaml_content):
    """生成 YAML 字符串，包含注释"""
    # 首先添加头部注释
    yaml_str = """# 合并后的 YAML 配置
# 生成时间: 自动生成

"""
    
    # 生成 YAML 内容
    yaml_str += yaml.dump(yaml_content, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    return yaml_str

def main():
    """主函数"""
    # 示例 YAML 内容，用户可以根据实际情况修改
    # 这里需要用户手动输入图片中的 YAML 内容
    yaml_contents = [
        {
            "key1": "value1",
            "key2": {
                "subkey1": "subvalue1",
                "subkey2": "subvalue2"
            },
            "key3": ["item1", "item2", "item3"]
        }
        # 可以添加更多 YAML 内容
    ]
    
    if not yaml_contents:
        logger.error("未提供 YAML 内容")
        return
    
    # 合并 YAML 内容
    merged = {}
    for content in yaml_contents:
        # 递归合并
        for key, value in content.items():
            if key in merged:
                if isinstance(merged[key], dict) and isinstance(value, dict):
                    # 递归合并字典
                    for subkey, subvalue in value.items():
                        merged[key][subkey] = subvalue
                elif isinstance(merged[key], list) and isinstance(value, list):
                    # 合并列表
                    merged[key].extend(value)
                else:
                    # 覆盖值
                    merged[key] = value
            else:
                merged[key] = value
    
    # 标准化键名
    normalized = normalize_keys(merged)
    
    # 添加注释
    with_comments = add_comments(normalized)
    
    # 生成 YAML
    yaml_str = generate_yaml(with_comments)
    
    # 保存结果
    with open('merged_yaml.yml', 'w', encoding='utf-8') as f:
        f.write(yaml_str)
    
    logger.info("合并后的 YAML 已保存到 merged_yaml.yml")
    print("\n合并后的 YAML 内容:")
    print(yaml_str)

if __name__ == "__main__":
    main()
