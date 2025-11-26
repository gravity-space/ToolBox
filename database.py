"""
数据库操作公共模块
提供SQLite数据库的全局引入和公共方法
"""
import sqlite3
import os
from typing import Any, List, Dict, Optional, Union, Tuple

# 默认数据库文件路径
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toolbox.db")


class DatabaseManager:
    """
    SQLite数据库管理器
    提供数据库连接管理和常用操作方法
    """
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """
        确保数据库文件和目录存在
        """
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    def connect(self) -> sqlite3.Connection:
        """
        创建数据库连接
        
        Returns:
            sqlite3.Connection: 数据库连接对象
        """
        return sqlite3.connect(self.db_path)
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行查询语句
        
        Args:
            query: SQL查询语句
            params: 查询参数
        
        Returns:
            List[Dict]: 查询结果列表，每行数据以字典形式返回
        """
        result = []
        conn = None
        
        try:
            conn = self.connect()
            conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # 获取所有结果
            rows = cursor.fetchall()
            # 转换为字典列表
            for row in rows:
                result.append(dict(row))
            
            return result
            
        except sqlite3.Error as e:
            print(f"查询错误: {e}")
            raise
            
        finally:
            if conn:
                conn.close()
    
    def execute_non_query(self, query: str, params: tuple = None) -> int:
        """
        执行非查询语句（INSERT, UPDATE, DELETE等）
        
        Args:
            query: SQL语句
            params: 查询参数
        
        Returns:
            int: 受影响的行数
        """
        conn = None
        
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            conn.commit()
            return cursor.rowcount
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            print(f"执行错误: {e}")
            raise
            
        finally:
            if conn:
                conn.close()
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        批量执行SQL语句
        
        Args:
            query: SQL语句
            params_list: 参数列表
        
        Returns:
            int: 受影响的总行数
        """
        conn = None
        
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            print(f"批量执行错误: {e}")
            raise
            
        finally:
            if conn:
                conn.close()
    
    def create_table(self, table_name: str, columns: Dict[str, str]):
        """
        创建表
        
        Args:
            table_name: 表名
            columns: 列定义字典 {列名: 列类型}
        """
        # 构建列定义字符串
        columns_str = ", ".join([f"{name} {col_type}" for name, col_type in columns.items()])
        
        # 构建创建表SQL
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
        
        # 执行SQL
        self.execute_non_query(create_sql)
    
    def drop_table(self, table_name: str):
        """
        删除表
        
        Args:
            table_name: 表名
        """
        drop_sql = f"DROP TABLE IF EXISTS {table_name}"
        self.execute_non_query(drop_sql)
    
    def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
        
        Returns:
            bool: 表是否存在
        """
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.execute_query(query, (table_name,))
        return len(result) > 0
    
    def get_tables(self) -> List[str]:
        """
        获取数据库中所有表名
        
        Returns:
            List[str]: 表名列表
        """
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        result = self.execute_query(query)
        return [row['name'] for row in result]
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, str]]:
        """
        获取表的列信息
        
        Args:
            table_name: 表名
        
        Returns:
            List[Dict]: 列信息列表
        """
        query = f"PRAGMA table_info({table_name})"
        return self.execute_query(query)


# 创建全局数据库管理器实例
db_manager = DatabaseManager()


# 导出公共函数
def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    """公共查询函数"""
    return db_manager.execute_query(query, params)


def execute_non_query(query: str, params: tuple = None) -> int:
    """公共非查询函数"""
    return db_manager.execute_non_query(query, params)


def execute_many(query: str, params_list: List[tuple]) -> int:
    """公共批量执行函数"""
    return db_manager.execute_many(query, params_list)


def create_table(table_name: str, columns: Dict[str, str]):
    """公共创建表函数"""
    return db_manager.create_table(table_name, columns)


def drop_table(table_name: str):
    """公共删除表函数"""
    return db_manager.drop_table(table_name)


def table_exists(table_name: str) -> bool:
    """公共检查表存在函数"""
    return db_manager.table_exists(table_name)


def get_tables() -> List[str]:
    """公共获取表列表函数"""
    return db_manager.get_tables()


def get_table_columns(table_name: str) -> List[Dict[str, str]]:
    """公共获取表列信息函数"""
    return db_manager.get_table_columns(table_name)


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return db_manager