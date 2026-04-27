#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从图片中提取 YAML 内容并合并
"""

import os
import pytesseract
from PIL import Image
import yaml
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('extract_yaml')

# 图片目录
IMAGE_DIR = 'common yaml data'

# 支持的图片格式
SUPPORTED_FORMATS = ('.HEIC', '.heic', '.jpg', '.jpeg', '.png', '.gif')

def extract_text_from_image(image_path):
    """从图片中提取文本"""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='eng')
        logger.info(f"成功从 {image_path} 提取文本")
        return text
    except Exception as e:
        logger.error(f"从 {image_path} 提取文本失败: {e}")
        # 当OCR失败时，返回空字符串
        return ""

def extract_yaml_from_text(text):
    """从文本中提取 YAML 内容"""
    try:
        # 尝试直接解析整个文本
        yaml_content = yaml.safe_load(text)
        if yaml_content:
            logger.info("成功解析 YAML 内容")
            return yaml_content
        else:
            logger.warning("未能解析 YAML 内容")
            return {}
    except yaml.YAMLError as e:
        logger.error(f"解析 YAML 失败: {e}")
        # 尝试提取 YAML 块
        lines = text.split('\n')
        yaml_lines = []
        in_yaml = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                yaml_lines.append(line)
            elif line and (':' in line or line in ['-', '']):
                yaml_lines.append(line)
                in_yaml = True
            elif in_yaml and not line:
                yaml_lines.append(line)
            elif in_yaml and line:
                yaml_lines.append(line)
        
        if yaml_lines:
            try:
                yaml_content = yaml.safe_load('\n'.join(yaml_lines))
                if yaml_content:
                    logger.info("成功从提取的行中解析 YAML 内容")
                    return yaml_content
            except yaml.YAMLError as e:
                logger.error(f"解析提取的 YAML 行失败: {e}")
        return {}

def process_images():
    """处理所有图片并提取 YAML 内容"""
    yaml_contents = []
    
    # 遍历图片目录
    for filename in os.listdir(IMAGE_DIR):
        if filename.endswith(SUPPORTED_FORMATS):
            image_path = os.path.join(IMAGE_DIR, filename)
            logger.info(f"处理图片: {filename}")
            
            # 提取文本
            text = extract_text_from_image(image_path)
            if text:
                # 提取 YAML
                yaml_content = extract_yaml_from_text(text)
                if yaml_content:
                    yaml_contents.append(yaml_content)
                    logger.info(f"从 {filename} 提取到 YAML 内容")
                else:
                    logger.warning(f"未能从 {filename} 提取 YAML 内容")
            else:
                logger.warning(f"未能从 {filename} 提取文本")
    
    # 如果没有提取到任何内容，提示用户手动输入
    if not yaml_contents:
        print("\n未能从图片中提取到YAML内容，请手动输入:")
        print("输入完成后，按Ctrl+D（Unix）或Ctrl+Z（Windows）结束输入")
        text = []
        try:
            while True:
                line = input()
                text.append(line)
        except EOFError:
            pass
        text = '\n'.join(text)
        if text:
            yaml_content = extract_yaml_from_text(text)
            if yaml_content:
                yaml_contents.append(yaml_content)
                logger.info("从手动输入中提取到 YAML 内容")
    
    return yaml_contents

def merge_yaml_contents(yaml_contents):
    """合并多个 YAML 内容"""
    merged = {}
    
    for content in yaml_contents:
        # 递归合并
        for key, value in content.items():
            if key in merged:
                if isinstance(merged[key], dict) and isinstance(value, dict):
                    # 递归合并字典
                    merged[key] = merge_dicts(merged[key], value)
                elif isinstance(merged[key], list) and isinstance(value, list):
                    # 合并列表
                    merged[key].extend(value)
                else:
                    # 覆盖值
                    merged[key] = value
            else:
                merged[key] = value
    
    return merged

def merge_dicts(a, b):
    """递归合并字典"""
    merged = a.copy()
    for key, value in b.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged

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
    # 处理图片
    yaml_contents = process_images()
    
    if not yaml_contents:
        logger.error("未能从任何图片中提取 YAML 内容")
        return
    
    # 合并 YAML 内容
    merged = merge_yaml_contents(yaml_contents)
    
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
