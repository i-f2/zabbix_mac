#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动YAML合并工具
用法：在下方的yaml_contents列表中填入每张图片的YAML内容
然后运行：python manual_merge.py
会自动合并、标准化键名（转换为snake_case）并保存为 merged_yaml.yml
"""

import yaml
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('yaml_merger')

def normalize_keys(data):
    """标准化键名，使用 snake_case"""
    if isinstance(data, dict):
        normalized = {}
        for key, value in data.items():
            snake_key = key.lower().replace(' ', '_')
            normalized[snake_key] = normalize_keys(value)
        return normalized
    elif isinstance(data, list):
        return [normalize_keys(item) for item in data]
    else:
        return data

def merge_yaml_contents(yaml_contents):
    """合并多个 YAML 内容"""
    merged = {}
    for content in yaml_contents:
        if not content:
            continue
        for key, value in content.items():
            if key in merged:
                if isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = merge_yaml_contents([merged[key], value])
                elif isinstance(merged[key], list) and isinstance(value, list):
                    merged[key].extend(value)
                else:
                    merged[key] = value
            else:
                merged[key] = value
    return merged

def main():
    # ==========================================
    # 请在这里填入每张图片的YAML内容
    # 格式：
    # yaml_contents = [
    #     {第一张图片的YAML内容},
    #     {第二张图片的YAML内容},
    #     ...
    # ]
    # ==========================================
    yaml_contents = [
        # 请将每张图片的YAML内容填在这里
        # 示例：
        # {
        #     "Items": {
        #         "system.cpu.util": {
        #             "name": "CPU utilization",
        #             "type": 0
        #         }
        #     }
        # },
        # {
        #     "Triggers": {
        #         ...
        #     }
        # },
    ]

    if not yaml_contents:
        logger.error("请先在yaml_contents中填入内容！")
        logger.info("\n使用说明：")
        logger.info("1. 打开common yaml data/ 文件夹中的图片")
        logger.info("2. 将每张图片的YAML内容复制到脚本中的yaml_contents列表")
        logger.info("3. 运行 python manual_merge.py")
        return

    logger.info("开始合并...")
    merged = merge_yaml_contents(yaml_contents)
    normalized = normalize_keys(merged)

    yaml_str = """# 合并后的 YAML 配置
# 生成时间: 自动生成
# 所有键已转换为 snake_case 格式

"""
    yaml_str += yaml.dump(normalized, default_flow_style=False, allow_unicode=True, sort_keys=False)

    with open('merged_yaml.yml', 'w', encoding='utf-8') as f:
        f.write(yaml_str)

    logger.info("\n✓ 合并完成！已保存到 merged_yaml.yml")
    logger.info("\n合并后的内容：\n")
    print(yaml_str)

if __name__ == "__main__":
    main()
