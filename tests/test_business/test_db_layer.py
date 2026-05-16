"""
tests/test_business/test_db_layer.py - 数据层通用函数测试
"""
import sys
sys.path.insert(0, '.')
import pytest
from helpers.db import (
    x1_query, x1_execute, x1_count, x1_get_by_id,
    x1_insert, x1_update, x1_delete, x1_transaction,
    get_x1_data_conn
)


class TestX1Query:
    def test_query_returns_list(self):
        """x1_query 返回 dict 列表"""
        result = x1_query("SELECT 1 as val")
        assert isinstance(result, list)
        assert result[0]['val'] == 1

    def test_query_one(self):
        """x1_query(one=True) 返回单条 dict"""
        result = x1_query("SELECT 42 as answer", one=True)
        assert result['answer'] == 42

    def test_query_one_empty(self):
        """x1_query(one=True) 无结果返回 None"""
        result = x1_query("SELECT * FROM business_projects WHERE id=-999", one=True)
        assert result is None

    def test_query_with_params(self):
        """x1_query 支持参数化"""
        result = x1_query("SELECT ? as x, ? as y", (10, 20), one=True)
        assert result['x'] == 10
        assert result['y'] == 20


class TestX1Count:
    def test_count_table(self):
        """x1_count 返回整数"""
        cnt = x1_count('business_projects')
        assert isinstance(cnt, int)
        assert cnt >= 0

    def test_count_with_where(self):
        """x1_count 支持 WHERE 条件"""
        cnt = x1_count('business_projects', "id > ?", (0,))
        assert isinstance(cnt, int)


class TestX1GetById:
    def test_existing(self):
        """x1_get_by_id 查询存在的记录"""
        # 先确认有数据
        cnt = x1_count('business_projects')
        if cnt > 0:
            first = x1_query("SELECT id FROM business_projects LIMIT 1", one=True)
            result = x1_get_by_id('business_projects', first['id'])
            assert result is not None
            assert result['id'] == first['id']

    def test_nonexistent(self):
        """x1_get_by_id 不存在返回 None"""
        result = x1_get_by_id('business_projects', -999)
        assert result is None


class TestX1Transaction:
    def test_transaction_commit(self):
        """事务正常提交"""
        with x1_transaction() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS _test_tx (id INTEGER PRIMARY KEY, val TEXT)"
            )
            conn.execute("INSERT OR REPLACE INTO _test_tx (id, val) VALUES (1, 'hello')")
        
        result = x1_query("SELECT val FROM _test_tx WHERE id=1", one=True)
        assert result['val'] == 'hello'
        
        # 清理
        x1_execute("DROP TABLE IF EXISTS _test_tx")

    def test_transaction_rollback(self):
        """事务异常回滚"""
        x1_execute("CREATE TABLE IF NOT EXISTS _test_tx2 (id INTEGER PRIMARY KEY, val TEXT)")
        x1_execute("INSERT OR REPLACE INTO _test_tx2 (id, val) VALUES (1, 'before')")
        
        try:
            with x1_transaction() as conn:
                conn.execute("UPDATE _test_tx2 SET val='during' WHERE id=1")
                raise ValueError("test rollback")
        except ValueError:
            pass
        
        result = x1_query("SELECT val FROM _test_tx2 WHERE id=1", one=True)
        assert result['val'] == 'before'
        
        # 清理
        x1_execute("DROP TABLE IF EXISTS _test_tx2")


class TestX1CRUD:
    def test_insert_and_delete(self):
        """x1_insert + x1_delete 完整流程"""
        x1_execute("CREATE TABLE IF NOT EXISTS _test_crud (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
        
        row_id = x1_insert('_test_crud', {'name': 'test_item'})
        assert row_id > 0
        
        record = x1_get_by_id('_test_crud', row_id)
        assert record['name'] == 'test_item'
        
        x1_delete('_test_crud', row_id)
        assert x1_get_by_id('_test_crud', row_id) is None
        
        x1_execute("DROP TABLE IF EXISTS _test_crud")

    def test_update(self):
        """x1_update 更新字段"""
        x1_execute("CREATE TABLE IF NOT EXISTS _test_upd (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, status TEXT)")
        
        row_id = x1_insert('_test_upd', {'name': 'original', 'status': 'draft'})
        x1_update('_test_upd', row_id, {'name': 'updated', 'status': 'done'})
        
        record = x1_get_by_id('_test_upd', row_id)
        assert record['name'] == 'updated'
        assert record['status'] == 'done'
        
        x1_execute("DROP TABLE IF EXISTS _test_upd")
