#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML合并工具 - 带有简单的命令行界面
"""

import os
import yaml
import logging
from PIL import Image

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('yaml_merger')

# 图片目录
IMAGE_DIR = 'common yaml data'

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

def generate_yaml(yaml_content):
    """生成 YAML 字符串，包含注释"""
    yaml_str = """# 合并后的 YAML 配置
# 生成时间: 自动生成
# 所有键已转换为 snake_case 格式

"""
    
    yaml_str += yaml.dump(yaml_content, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    return yaml_str

def merge_yaml_contents(yaml_contents):
    """合并多个 YAML 内容"""
    merged = {}
    
    for content in yaml_contents:
        for key, value in content.items():
            if key in merged:
                if isinstance(merged[key], dict) and isinstance(value, dict):
                    # 递归合并字典
                    merged[key] = merge_yaml_contents([merged[key], value])
                elif isinstance(merged[key], list) and isinstance(value, list):
                    # 合并列表
                    merged[key].extend(value)
                else:
                    # 覆盖值
                    merged[key] = value
            else:
                merged[key] = value
    
    return merged

def list_images():
    """列出所有图片文件"""
    images = []
    if os.path.exists(IMAGE_DIR):
        for filename in os.listdir(IMAGE_DIR):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                images.append(filename)
        images.sort()
    return images

def main():
    """主函数"""
    print("=" * 60)
    print("YAML合并工具")
    print("=" * 60)
    
    # 列出图片
    images = list_images()
    
    if not images:
        print(f"未在 '{IMAGE_DIR}' 目录中找到图片文件。")
        return
    
    print(f"\n找到 {len(images)} 张图片：")
    for i, img in enumerate(images, 1):
        print(f"  {i}. {img}")
    
    print("\n" + "=" * 60)
    print("请按照以下步骤操作：")
    print("1. 查看 'common yaml data' 文件夹中的图片")
    print("2. 将每张图片中的 YAML 内容复制到下方")
    print("3. 完成后输入 'done' 进行合并")
    print("=" * 60)
    
    yaml_contents = []
    image_index = 0
    
    while image_index < len(images):
        current_image = images[image_index]
        print(f"\n--- 第 {image_index + 1}/{len(images)} 张图片: {current_image} ---")
        print("请输入图片中的 YAML 内容（输入 'skip' 跳过，'done' 完成所有）：")
        
        lines = []
        while True:
            try:
                line = input()
                if line.lower() == 'skip':
                    print("跳过此图片。")
                    break
                if line.lower() == 'done':
                    print("完成所有输入。")
                    image_index = len(images)  # 结束循环
                    break
                lines.append(line)
            except EOFError:
                break
        
        if lines:
            yaml_text = '\n'.join(lines)
            try:
                yaml_content = yaml.safe_load(yaml_text)
                if yaml_content:
                    yaml_contents.append(yaml_content)
                    print(f"✓ 成功解析 YAML 内容")
                    image_index += 1
                else:
                    print("✗ YAML 内容为空，未添加。")
            except yaml.YAMLError as e:
                print(f"✗ 解析 YAML 失败: {e}")
                print("请重新输入，或输入 'skip' 跳过。")
        elif image_index < len(images) and images[image_index] == current_image:
            # 如果没有输入内容且不是 'done'，递增索引
            image_index += 1
    
    if not yaml_contents:
        print("\n没有输入任何 YAML 内容。")
        return
    
    print("\n" + "=" * 60)
    print("合并中...")
    
    # 合并 YAML 内容
    merged = merge_yaml_contents(yaml_contents)
    
    # 标准化键名
    normalized = normalize_keys(merged)
    
    # 生成 YAML
    yaml_str = generate_yaml(normalized)
    
    # 保存结果
    output_file = 'merged_yaml.yml'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(yaml_str)
    
    print(f"\n✓ 合并完成！结果已保存到: {output_file}")
    print("\n" + "=" * 60)
    print("合并后的 YAML 内容：")
    print("=" * 60)
    print(yaml_str)

if __name__ == "__main__":
    main()
