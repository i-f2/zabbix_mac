#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web界面的YAML合并工具 - 简化版
"""

import os
import yaml
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('web_yaml_merger')

# 图片目录
IMAGE_DIR = 'common yaml data'
PORT = 8001

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

class YAMLMergerHandler(SimpleHTTPRequestHandler):
    """自定义HTTP请求处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/':
            self.serve_main_page()
        elif self.path.startswith('/images/'):
            self.serve_image()
        else:
            super().do_GET()
    
    def do_POST(self):
        """处理POST请求"""
        if self.path == '/merge':
            self.handle_merge()
        else:
            self.send_error(404, "Not found")
    
    def serve_main_page(self):
        """提供主页面"""
        images = list_images()
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YAML合并工具</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        .container {{
            display: flex;
            gap: 20px;
            margin-top: 20px;
        }}
        .image-panel {{
            flex: 1;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .input-panel {{
            flex: 1;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        textarea {{
            width: 100%;
            height: 300px;
            font-family: monospace;
            font-size: 14px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            resize: vertical;
        }}
        .btn {{
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
        }}
        .btn:hover {{
            background-color: #45a049;
        }}
        .btn-secondary {{
            background-color: #2196F3;
        }}
        .btn-secondary:hover {{
            background-color: #0b7dda;
        }}
        .btn-danger {{
            background-color: #f44336;
        }}
        .btn-danger:hover {{
            background-color: #da190b;
        }}
        .btn-warning {{
            background-color: #ff9800;
        }}
        .btn-warning:hover {{
            background-color: #e68900;
        }}
        .image-nav {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .submitted-list {{
            margin-top: 20px;
            max-height: 300px;
            overflow-y: auto;
        }}
        .submitted-item {{
            background: #f9f9f9;
            padding: 10px;
            margin: 5px 0;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
        }}
        .result {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-top: 20px;
        }}
        pre {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            white-space: pre-wrap;
        }}
        .progress {{
            text-align: center;
            font-size: 18px;
            margin-bottom: 10px;
            color: #666;
        }}
        .status {{
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }}
        .status.success {{
            background: #dff0d8;
            color: #3c763d;
        }}
        .status.error {{
            background: #f2dede;
            color: #a94442;
        }}
    </style>
</head>
<body>
    <h1>YAML合并工具</h1>
    
    <div class="container">
        <div class="image-panel">
            <div class="image-nav">
                <button class="btn btn-secondary" onclick="prevImage()">← 上一张</button>
                <span id="imageCounter" class="progress">1/{len(images)}</span>
                <button class="btn btn-secondary" onclick="nextImage()">下一张 →</button>
            </div>
            <div id="imageContainer">
                <img id="currentImage" src="/images/{images[0] if images else ''}" alt="图片" style="display: {'block' if images else 'none'}">
                <p id="noImage" style="display: {'none' if images else 'block'}; text-align: center; color: #666;">没有找到图片</p>
            </div>
        </div>
        
        <div class="input-panel">
            <h3>图片: <span id="currentImageName">{images[0] if images else ''}</span></h3>
            <p>请将图片中的YAML内容复制到下方：</p>
            <textarea id="yamlInput" placeholder="在此输入YAML内容..."></textarea>
            <br>
            <button class="btn" onclick="addYAML()">✓ 添加此YAML</button>
            <button class="btn btn-warning" onclick="skipImage()">跳过</button>
            <button class="btn btn-danger" onclick="clearAll()">清空全部</button>
            <button class="btn btn-secondary" onclick="mergeYAML()">🔄 合并所有</button>
            
            <div class="submitted-list">
                <h4>已添加的YAML (<span id="submittedCount">0</span>):</h4>
                <div id="submittedList"></div>
            </div>
            
            <div id="statusArea"></div>
        </div>
    </div>
    
    <div class="result" id="resultSection" style="display: none;">
        <h2>✅ 合并结果</h2>
        <button class="btn btn-secondary" onclick="mergeYAML()">重新合并</button>
        <button class="btn" onclick="downloadYAML()">⬇️ 下载 merged_yaml.yml</button>
        <pre id="resultOutput"></pre>
    </div>
    
    <script>
        const images = {json.dumps(images)};
        let currentIndex = 0;
        let allYAMLs = [];
        
        function updateImage() {{
            if (images.length > 0) {{
                document.getElementById('currentImage').src = '/images/' + images[currentIndex];
                document.getElementById('currentImage').style.display = 'block';
                document.getElementById('noImage').style.display = 'none';
                document.getElementById('currentImageName').textContent = images[currentIndex];
                document.getElementById('imageCounter').textContent = (currentIndex + 1) + '/' + images.length;
            }}
        }}
        
        function prevImage() {{
            if (currentIndex > 0) {{
                currentIndex--;
                updateImage();
            }}
        }}
        
        function nextImage() {{
            if (currentIndex < images.length - 1) {{
                currentIndex++;
                updateImage();
            }}
        }}
        
        function addYAML() {{
            const yamlText = document.getElementById('yamlInput').value.trim();
            if (!yamlText) {{
                showStatus('请输入YAML内容', 'error');
                return;
            }}
            
            try {{
                const parsed = jsyaml.load(yamlText);
                if (!parsed) {{
                    showStatus('YAML内容无效或为空', 'error');
                    return;
                }}
                
                allYAMLs.push({{
                    image: images[currentIndex],
                    yaml: yamlText,
                    parsed: parsed
                }});
                
                updateList();
                document.getElementById('yamlInput').value = '';
                showStatus('✅ 已添加YAML内容', 'success');
                
                if (currentIndex < images.length - 1) {{
                    nextImage();
                }}
            }} catch (e) {{
                showStatus('YAML解析错误: ' + e.message, 'error');
            }}
        }}
        
        function skipImage() {{
            if (currentIndex < images.length - 1) {{
                nextImage();
            }}
        }}
        
        function updateList() {{
            const list = document.getElementById('submittedList');
            list.innerHTML = '';
            allYAMLs.forEach((item, index) => {{
                const div = document.createElement('div');
                div.className = 'submitted-item';
                div.innerHTML = `<strong>${{index + 1}}. ${{item.image}}</strong>
                    <button onclick="removeYAML(${{index}})" style="float:right; background:#f44336; color:white; border:none; border-radius:3px; cursor:pointer; padding:2px 8px;">×</button>
                    <pre style="margin:5px 0; font-size:12px; white-space:pre-wrap;">${{item.yaml.substring(0, 150)}}${{item.yaml.length > 150 ? '...' : ''}}</pre>`;
                list.appendChild(div);
            }});
            document.getElementById('submittedCount').textContent = allYAMLs.length;
        }}
        
        function removeYAML(index) {{
            allYAMLs.splice(index, 1);
            updateList();
        }}
        
        function clearAll() {{
            if (confirm('确定要清空所有内容吗？')) {{
                allYAMLs = [];
                updateList();
                document.getElementById('yamlInput').value = '';
                document.getElementById('resultSection').style.display = 'none';
                document.getElementById('statusArea').innerHTML = '';
            }}
        }}
        
        function showStatus(message, type) {{
            const area = document.getElementById('statusArea');
            area.innerHTML = `<div class="status ${{type}}">${{message}}</div>`;
            setTimeout(() => {{ area.innerHTML = ''; }}, 3000);
        }}
        
        function mergeYAML() {{
            if (allYAMLs.length === 0) {{
                showStatus('请先添加至少一个YAML内容', 'error');
                return;
            }}
            
            const dataToSend = allYAMLs.map(item => ({{ yaml: item.yaml }}));
            
            fetch('/merge', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify(dataToSend)
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    document.getElementById('resultOutput').textContent = data.result;
                    document.getElementById('resultSection').style.display = 'block';
                    showStatus('✅ 合并成功！', 'success');
                }} else {{
                    showStatus('合并失败: ' + data.error, 'error');
                }}
            }})
            .catch(error => {{
                showStatus('请求失败: ' + error, 'error');
            }});
        }}
        
        function downloadYAML() {{
            const content = document.getElementById('resultOutput').textContent;
            const blob = new Blob([content], {{ type: 'text/yaml;charset=utf-8' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'merged_yaml.yml';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}
        
        // 初始化
        updateImage();
    </script>
    <script src="https://cdn.jsdelivr.net/npm/js-yaml@4.1.0/dist/js-yaml.min.js"></script>
</body>
</html>
"""
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_image(self):
        """提供图片"""
        image_name = self.path[len('/images/'):]
        image_path = os.path.join(IMAGE_DIR, image_name)
        
        if os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'image/png' if image_name.lower().endswith('.png') else 'image/jpeg')
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, "Image not found")
    
    def handle_merge(self):
        """处理YAML合并"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        try:
            yaml_contents = []
            for item in data:
                yaml_content = yaml.safe_load(item['yaml'])
                if yaml_content:
                    yaml_contents.append(yaml_content)
            
            if not yaml_contents:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': '没有有效的YAML内容'}).encode('utf-8'))
                return
            
            merged = merge_yaml_contents(yaml_contents)
            normalized = normalize_keys(merged)
            
            yaml_str = """# 合并后的 YAML 配置
# 生成时间: 自动生成
# 所有键已转换为 snake_case 格式

"""
            yaml_str += yaml.dump(normalized, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # 保存到文件
            with open('merged_yaml.yml', 'w', encoding='utf-8') as f:
                f.write(yaml_str)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'result': yaml_str}).encode('utf-8'))
            
        except Exception as e:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode('utf-8'))

def main():
    """主函数"""
    images = list_images()
    print(f"找到 {len(images)} 张图片")
    
    print(f"\n启动Web服务器在端口 {PORT}...")
    print(f"请在浏览器中打开: http://localhost:{PORT}")
    print("按 Ctrl+C 停止服务器\n")
    
    # 确保我们在正确的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, YAMLMergerHandler)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        httpd.server_close()

if __name__ == "__main__":
    main()
