# -*- coding: utf-8 -*-
"""
Flask 应用测试 - Web 管理界面测试
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def app():
    """创建测试 Flask 应用"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # 模拟 fetchall 返回空列表，让各个页面正常渲染
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch('app.get_db_connection', return_value=mock_conn):
        from app import app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        yield app


@pytest.fixture
def client(app):
    """测试客户端"""
    return app.test_client()


class TestAppBasicRoutes:
    """基础路由测试"""

    def test_index_page(self, client):
        """首页访问"""
        resp = client.get('/')
        assert resp.status_code == 200

    def test_system_info(self, client):
        """系统信息页"""
        resp = client.get('/system-info')
        assert resp.status_code == 200

    def test_templates_page(self, client):
        """模板管理页（需要 mock 数据库查询）"""
        resp = client.get('/templates')
        assert resp.status_code == 200

    def test_nonexistent_template(self, client):
        """不存在的模板"""
        resp = client.get('/template/99999')
        assert resp.status_code == 302  # 重定回到模板列表

    def test_hosts_page(self, client):
        """主机列表页"""
        resp = client.get('/hosts')
        assert resp.status_code == 200


class TestAppItems:
    """监控项管理测试"""

    def test_items_list(self, client):
        """监控项列表"""
        resp = client.get('/items')
        assert resp.status_code == 200

    def test_items_review(self, client):
        """监控项复核表"""
        resp = client.get('/items-review')
        assert resp.status_code == 200

    def test_item_add_page(self, client):
        """添加监控项页面"""
        resp = client.get('/item/add')
        assert resp.status_code == 200

    def test_item_add_post(self, client):
        """提交添加监控项（表单字段名为 item_key）"""
        resp = client.post('/item/add', data={
            'item_key': 'test.item',
            'name': 'Test Item',
            'type': 0,
            'value_type': 3,
            'delay': '60',
            'template_name': 'Template OS Linux'
        }, follow_redirects=True)
        assert resp.status_code in (200, 302)


class TestAppTriggers:
    """触发器管理测试"""

    def test_triggers_list(self, client):
        """触发器列表"""
        resp = client.get('/triggers')
        assert resp.status_code == 200

    def test_triggers_review(self, client):
        """触发器复核表"""
        resp = client.get('/triggers-review')
        assert resp.status_code == 200

    def test_trigger_add_page(self, client):
        """添加触发器页面"""
        resp = client.get('/trigger/add')
        assert resp.status_code == 200


class TestAppHosts:
    """主机管理测试"""

    def test_add_host_page(self, client):
        """添加主机页面"""
        resp = client.get('/host/add')
        assert resp.status_code == 200

    def test_hosts_page(self, client):
        """主机列表"""
        resp = client.get('/hosts')
        assert resp.status_code == 200


class TestAppPrototypes:
    """原型管理测试"""

    def test_item_prototypes_page(self, client):
        """监控项原型列表"""
        resp = client.get('/item-prototypes')
        assert resp.status_code == 200

    def test_trigger_prototypes_page(self, client):
        """触发器原型列表"""
        resp = client.get('/trigger-prototypes')
        assert resp.status_code == 200

    def test_item_prototypes_review(self, client):
        """监控项原型复核表"""
        resp = client.get('/item-prototypes-review')
        assert resp.status_code == 200

    def test_trigger_prototypes_review(self, client):
        """触发器原型复核表"""
        resp = client.get('/trigger-prototypes-review')
        assert resp.status_code == 200
