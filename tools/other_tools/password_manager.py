"""
密码管理器工具模块
提供密码的安全存储、管理和生成功能
"""
import os
import sys
import string
import secrets
import base64
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox,
    QGroupBox, QGridLayout, QCheckBox, QInputDialog, QDateEdit, QTextEdit
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QIcon

# 导入数据库模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database import execute_query, execute_non_query, create_table, table_exists


class PasswordEncryption:
    """
    密码加密工具类
    使用AES-256-CBC加密算法保护密码
    """
    # 主密码相关常量
    SALT_LENGTH = 32
    KEY_LENGTH = 32
    ITERATIONS = 100000
    
    # 当前会话使用的加密密钥
    _session_key = None
    
    @staticmethod
    def set_session_key(key):
        """设置当前会话的加密密钥"""
        PasswordEncryption._session_key = key
    
    @staticmethod
    def get_session_key():
        """获取当前会话的加密密钥"""
        return PasswordEncryption._session_key
    
    @staticmethod
    def generate_key():
        """生成随机密钥"""
        return os.urandom(32)  # 256位密钥
    
    @staticmethod
    def get_encryption_key():
        """获取加密密钥
        
        如果会话中已设置密钥（通过主密码派生），则使用会话密钥
        否则使用默认密钥（用于首次设置主密码时）
        """
        if PasswordEncryption._session_key:
            return PasswordEncryption._session_key
        
        # 默认密钥，仅用于首次设置主密码时
        app_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        key_bytes = (app_path * 10)[:32].encode('utf-8')
        return key_bytes
    
    @staticmethod
    def create_master_password_hash(master_password):
        """
        创建主密码的哈希值和盐值
        
        Args:
            master_password: 主密码
            
        Returns:
            tuple: (salt, hashed_password)
        """
        # 生成随机盐值
        salt = os.urandom(PasswordEncryption.SALT_LENGTH)
        
        # 使用PBKDF2生成密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=PasswordEncryption.KEY_LENGTH,
            salt=salt,
            iterations=PasswordEncryption.ITERATIONS,
            backend=default_backend()
        )
        hashed_password = kdf.derive(master_password.encode('utf-8'))
        
        return base64.b64encode(salt).decode('utf-8'), base64.b64encode(hashed_password).decode('utf-8')
    
    @staticmethod
    def verify_master_password(master_password, salt, hashed_password):
        """
        验证主密码
        
        Args:
            master_password: 要验证的主密码
            salt: 存储的盐值
            hashed_password: 存储的哈希密码
            
        Returns:
            bool: 密码是否正确
        """
        try:
            # 解码盐值和哈希密码
            salt_bytes = base64.b64decode(salt)
            hashed_password_bytes = base64.b64decode(hashed_password)
            
            # 使用PBKDF2生成密钥
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=PasswordEncryption.KEY_LENGTH,
                salt=salt_bytes,
                iterations=PasswordEncryption.ITERATIONS,
                backend=default_backend()
            )
            
            # 验证密码
            kdf.verify(master_password.encode('utf-8'), hashed_password_bytes)
            return True
        except Exception:
            return False
    
    @staticmethod
    def derive_key_from_master_password(master_password, salt):
        """
        从主密码派生加密密钥
        
        Args:
            master_password: 主密码
            salt: 盐值
            
        Returns:
            bytes: 派生的加密密钥
        """
        salt_bytes = base64.b64decode(salt)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=PasswordEncryption.KEY_LENGTH,
            salt=salt_bytes,
            iterations=PasswordEncryption.ITERATIONS,
            backend=default_backend()
        )
        
        return kdf.derive(master_password.encode('utf-8'))
    
    @staticmethod
    def encrypt(password, key=None):
        """
        加密密码
        
        Args:
            password: 要加密的密码
            key: 加密密钥，如果不提供则使用默认密钥
        
        Returns:
            str: 加密后的密码（base64编码）
        """
        if key is None:
            key = PasswordEncryption.get_encryption_key()
        
        # 生成随机IV
        iv = os.urandom(16)
        
        # 创建填充器
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(password.encode('utf-8')) + padder.finalize()
        
        # 创建密码器并加密
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # 返回IV和密文的base64编码
        return base64.b64encode(iv + ciphertext).decode('utf-8')
    
    @staticmethod
    def decrypt(encrypted_password, key=None):
        """
        解密密码
        
        Args:
            encrypted_password: 加密后的密码（base64编码）
            key: 解密密钥，如果不提供则使用默认密钥
        
        Returns:
            str: 解密后的密码
        """
        if key is None:
            key = PasswordEncryption.get_encryption_key()
        
        # 解码base64
        raw_data = base64.b64decode(encrypted_password.encode('utf-8'))
        
        # 提取IV和密文
        iv = raw_data[:16]
        ciphertext = raw_data[16:]
        
        # 创建密码器并解密
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # 移除填充
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data.decode('utf-8')


class PasswordGenerator:
    """
    密码生成工具类
    """
    
    @staticmethod
    def generate_password(length=16, use_uppercase=True, use_lowercase=True,
                         use_digits=True, use_special=True, exclude_similar=True):
        """
        生成随机密码
        
        Args:
            length: 密码长度
            use_uppercase: 是否使用大写字母
            use_lowercase: 是否使用小写字母
            use_digits: 是否使用数字
            use_special: 是否使用特殊字符
            exclude_similar: 是否排除相似字符
        
        Returns:
            str: 生成的密码
        """
        # 定义字符集
        chars = ''
        if use_uppercase:
            chars += string.ascii_uppercase
        if use_lowercase:
            chars += string.ascii_lowercase
        if use_digits:
            chars += string.digits
        if use_special:
            chars += '!@#$%^&*()_+-=[]{}|;:,.<>?'
        
        # 如果没有选择任何字符集，默认使用大小写字母和数字
        if not chars:
            chars = string.ascii_letters + string.digits
        
        # 排除相似字符
        if exclude_similar:
            similar_chars = 'il1Lo0O'
            for c in similar_chars:
                chars = chars.replace(c, '')
        
        # 确保密码包含所有选定类型的字符
        password = []
        required_chars = []
        
        if use_uppercase:
            required_chars.append(secrets.choice(string.ascii_uppercase))
        if use_lowercase:
            required_chars.append(secrets.choice(string.ascii_lowercase))
        if use_digits:
            required_chars.append(secrets.choice(string.digits))
        if use_special:
            required_chars.append(secrets.choice('!@#$%^&*()_+-=[]{}|;:,.<>?'))
        
        # 添加剩余的随机字符
        remaining_length = max(0, length - len(required_chars))
        for _ in range(remaining_length):
            password.append(secrets.choice(chars))
        
        # 合并并打乱字符顺序
        password.extend(required_chars)
        
        # 使用secrets实现类似shuffle的功能
        # Fisher-Yates 洗牌算法的密码学安全实现
        for i in range(len(password) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            password[i], password[j] = password[j], password[i]
        
        return ''.join(password)


class PasswordManagerDialog(QDialog):
    """
    密码管理器对话框
    提供密码的安全存储、管理和生成功能
    """
    
    def __init__(self, parent=None):
        """
        初始化密码管理器对话框
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        
        # 初始化数据库
        self._init_database()
        
        # 检查并设置/验证主密码
        if not self._check_and_setup_master_password():
            # 如果主密码验证失败或用户取消，立即关闭对话框
            self.setModal(False)  # 确保不会阻塞父窗口
            self.reject()  # 拒绝对话框
            self.close()  # 直接关闭对话框
            return
        
        # 从config.json中获取窗口标题（使用工具名称）
        window_title = "密码管理器"  # 默认标题
        if parent and hasattr(parent, 'tools'):
            # 查找当前工具的配置
            for tool in parent.tools:
                if tool.class_name == 'PasswordManagerDialog':
                    window_title = tool.name
                    break
        # 设置窗口标题和大小
        self.setWindowTitle(window_title)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)
        
        # 初始化UI
        self.init_ui()
        
        # 加载密码数据
        self.load_passwords()
    
    def center_window(self):
        """将窗口设置在屏幕中央"""
        # 获取屏幕可用几何区域
        screen_geometry = self.screen().availableGeometry()
        # 获取窗口大小
        window_geometry = self.frameGeometry()
        # 计算中心点
        center_point = screen_geometry.center()
        # 将窗口中心移动到屏幕中心
        window_geometry.moveCenter(center_point)
        # 应用位置
        self.move(window_geometry.topLeft())
    
    def _check_and_setup_master_password(self):
        """
        检查是否需要设置主密码或验证现有主密码
        
        Returns:
            bool: 如果主密码设置/验证成功返回True，否则返回False
        """
        # 检查master_passwords表是否存在
        if not table_exists('master_passwords'):
            # 创建主密码表
            columns = {
                'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                'salt': 'TEXT NOT NULL',
                'hashed_password': 'TEXT NOT NULL',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            create_table('master_passwords', columns)
        
        # 检查是否已有主密码
        master_password_data = execute_query('SELECT * FROM master_passwords LIMIT 1')
        
        if not master_password_data:
            # 首次使用，需要设置主密码
            return self._set_master_password()
        else:
            # 已有主密码，需要验证
            return self._verify_master_password(master_password_data[0])
    
    def _set_master_password(self):
        """
        设置主密码对话框
        
        Returns:
            bool: 如果主密码设置成功返回True
        """
        # 创建设置主密码的对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("设置主密码")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # 添加说明文本
        info_label = QLabel("欢迎使用密码管理器！\n请设置一个主密码来保护您的密码数据。\n主密码非常重要，请务必记住！")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 表单布局
        form_layout = QGridLayout()
        
        # 主密码
        form_layout.addWidget(QLabel("主密码:"), 0, 0)
        master_password_edit = QLineEdit()
        master_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        master_password_edit.setPlaceholderText("请输入至少8位的密码")
        form_layout.addWidget(master_password_edit, 0, 1)
        
        # 确认主密码
        form_layout.addWidget(QLabel("确认主密码:"), 1, 0)
        confirm_password_edit = QLineEdit()
        confirm_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(confirm_password_edit, 1, 1)
        
        # 显示密码复选框
        show_pass_check = QCheckBox("显示密码")
        show_pass_check.stateChanged.connect(lambda state: 
            (master_password_edit.setEchoMode(QLineEdit.EchoMode.Normal if state else QLineEdit.EchoMode.Password),
             confirm_password_edit.setEchoMode(QLineEdit.EchoMode.Normal if state else QLineEdit.EchoMode.Password)))
        form_layout.addWidget(show_pass_check, 2, 1)
        
        layout.addLayout(form_layout)
        
        # 按钮布局
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_button)
        
        ok_button = QPushButton("确定")
        ok_button.setDefault(True)
        buttons_layout.addWidget(ok_button)
        
        layout.addLayout(buttons_layout)
        
        # 验证输入并保存主密码
        def validate_and_save():
            master_password = master_password_edit.text()
            confirm_password = confirm_password_edit.text()
            
            # 验证密码长度
            if len(master_password) < 8:
                QMessageBox.warning(dialog, "警告", "主密码长度至少为8位")
                return
            
            # 验证两次输入是否一致
            if master_password != confirm_password:
                QMessageBox.warning(dialog, "警告", "两次输入的密码不一致")
                return
            
            # 生成盐值和哈希密码
            salt, hashed_password = PasswordEncryption.create_master_password_hash(master_password)
            
            # 保存到数据库
            try:
                execute_non_query(
                    'INSERT INTO master_passwords (salt, hashed_password) VALUES (?, ?)',
                    (salt, hashed_password)
                )
                
                # 从主密码派生并设置会话密钥
                session_key = PasswordEncryption.derive_key_from_master_password(master_password, salt)
                PasswordEncryption.set_session_key(session_key)
                
                dialog.accept()
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"保存主密码失败: {str(e)}")
        
        ok_button.clicked.connect(validate_and_save)
        
        # 显示对话框
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
    
    def _verify_master_password(self, master_password_data):
        """
        验证主密码
        
        Args:
            master_password_data: 主密码数据字典
            
        Returns:
            bool: 如果验证成功返回True
        """
        salt = master_password_data['salt']
        hashed_password = master_password_data['hashed_password']
        
        # 最多尝试5次（仅在密码验证失败时计数）
        failed_attempts = 0
        
        while failed_attempts < 5:
            # 创建验证对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("验证主密码")
            dialog.setMinimumWidth(350)
            
            layout = QVBoxLayout(dialog)
            
            # 添加说明文本
            remaining_attempts = 5 - failed_attempts
            info_text = f"请输入主密码来访问您的密码数据。\n剩余尝试次数: {remaining_attempts}"
            if remaining_attempts < 5:
                info_text += "\n请注意：连续输入错误5次将清空所有密码数据！"
            
            info_label = QLabel(info_text)
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            # 密码输入
            password_edit = QLineEdit()
            password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            password_edit.setPlaceholderText("请输入主密码")
            password_edit.setMinimumHeight(30)
            layout.addWidget(password_edit)
            
            # 显示密码复选框
            show_pass_check = QCheckBox("显示密码")
            show_pass_check.stateChanged.connect(lambda state: 
                password_edit.setEchoMode(QLineEdit.EchoMode.Normal if state else QLineEdit.EchoMode.Password))
            layout.addWidget(show_pass_check)
            
            # 按钮布局
            buttons_layout = QHBoxLayout()
            buttons_layout.addStretch()
            
            cancel_button = QPushButton("取消")
            cancel_button.clicked.connect(dialog.reject)
            buttons_layout.addWidget(cancel_button)
            
            ok_button = QPushButton("确定")
            ok_button.setDefault(True)
            buttons_layout.addWidget(ok_button)
            
            layout.addLayout(buttons_layout)
            
            # 验证密码
            def validate_password():
                password = password_edit.text()
                
                if not password:
                    QMessageBox.warning(dialog, "警告", "请输入主密码")
                    return
                
                # 验证密码
                if PasswordEncryption.verify_master_password(password, salt, hashed_password):
                    # 密码正确，派生会话密钥
                    session_key = PasswordEncryption.derive_key_from_master_password(password, salt)
                    PasswordEncryption.set_session_key(session_key)
                    dialog.accept()
                else:
                    # 密码验证失败，立即增加失败计数
                    nonlocal failed_attempts
                    failed_attempts += 1
                    
                    # 更新剩余尝试次数显示
                    remaining_attempts = 5 - failed_attempts
                    info_label.setText(f"请输入主密码来访问您的密码数据。\n剩余尝试次数: {remaining_attempts}\n请注意：连续输入错误5次将清空所有密码数据！")
                    
                    # 如果达到最大失败次数，清空数据
                    if failed_attempts >= 5:
                        dialog.accept()
                    else:
                        QMessageBox.warning(dialog, "验证失败", "主密码不正确")
                        # 清空密码输入框，让用户可以再次尝试
                        password_edit.clear()
                        password_edit.setFocus()
            
            
            ok_button.clicked.connect(validate_password)
            # 允许按Enter键验证
            password_edit.returnPressed.connect(validate_password)
            
            # 显示对话框
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted:
                # 如果密码正确则返回True，如果达到最大失败次数也会接受但需要清空数据
                if PasswordEncryption.get_session_key() is not None:
                    return True
            else:
                # 用户取消或关闭窗口，直接返回False，不显示确认对话框
                return False
        
        # 所有尝试都失败，清空所有密码数据
        self._clear_all_passwords()
        QMessageBox.critical(self, "验证失败", "主密码连续验证失败5次，所有密码数据已清空。应用将关闭。")
        self.reject()  # 确保对话框被拒绝
        return False
    
    def _clear_all_passwords(self):
        """
        清空所有密码数据
        """
        try:
            # 删除所有密码
            execute_non_query('DELETE FROM passwords')
            # 重置密码表的自增ID
            execute_non_query('DELETE FROM sqlite_sequence WHERE name="passwords"')
        except Exception as e:
            print(f"清空密码数据时出错: {str(e)}")
    
    def _init_database(self):
        """
        初始化数据库表结构
        """
        # 检查密码表是否存在，如果不存在则创建
        if not table_exists('passwords'):
            columns = {
                'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                'title': 'TEXT NOT NULL',
                'username': 'TEXT',
                'encrypted_password': 'TEXT NOT NULL',
                'url': 'TEXT',
                'category': 'TEXT',
                'notes': 'TEXT',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'expires_at': 'DATE',
                'is_favorite': 'INTEGER DEFAULT 0'
            }
            create_table('passwords', columns)
        
        # 检查分类表是否存在，如果不存在则创建
        if not table_exists('categories'):
            columns = {
                'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                'name': 'TEXT NOT NULL UNIQUE'
            }
            create_table('categories', columns)
            
            # 添加默认分类
            default_categories = ['网站', '应用程序', '银行账户', '电子邮箱', '社交媒体', '其他']
            for category in default_categories:
                execute_non_query(
                    'INSERT OR IGNORE INTO categories (name) VALUES (?)',
                    (category,)
                )
    
    def init_ui(self):
        """
        初始化用户界面
        """
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 1. 工具栏区域
        toolbar_layout = QHBoxLayout()
        
        # 添加按钮
        self.add_button = QPushButton("添加密码")
        self.add_button.clicked.connect(self.add_password)
        toolbar_layout.addWidget(self.add_button)
        
        # 编辑按钮
        self.edit_button = QPushButton("编辑密码")
        self.edit_button.clicked.connect(self.edit_password)
        toolbar_layout.addWidget(self.edit_button)
        
        # 删除按钮
        self.delete_button = QPushButton("删除密码")
        self.delete_button.clicked.connect(self.delete_password)
        toolbar_layout.addWidget(self.delete_button)
        
        # 生成密码按钮
        self.generate_button = QPushButton("生成密码")
        self.generate_button.clicked.connect(self.show_password_generator)
        toolbar_layout.addWidget(self.generate_button)
        
        # 刷新按钮
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.load_passwords)
        toolbar_layout.addWidget(self.refresh_button)
        
        # 分类筛选
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(QLabel("分类:"))
        self.category_filter = QComboBox()
        self.category_filter.currentIndexChanged.connect(self.filter_by_category)
        toolbar_layout.addWidget(self.category_filter)
        
        # 搜索框
        toolbar_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索标题、用户名或URL...")
        self.search_edit.textChanged.connect(self.search_passwords)
        toolbar_layout.addWidget(self.search_edit)
        
        main_layout.addLayout(toolbar_layout)
        
        # 2. 密码表格
        self.password_table = QTableWidget()
        self.password_table.setColumnCount(8)
        self.password_table.setHorizontalHeaderLabels([
            "标题", "用户名", "密码", "URL", "分类", "创建日期", "过期日期", "收藏"
        ])
        
        # 设置表格属性
        self.password_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.password_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.password_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.password_table.cellClicked.connect(self.on_cell_clicked)
        
        main_layout.addWidget(self.password_table)
        
        # 加载分类数据
        self.load_categories()
        
        # 将窗口设置在屏幕中央
        self.center_window()
    
    def load_categories(self):
        """
        加载分类数据
        """
        self.category_filter.clear()
        self.category_filter.addItem("全部")
        
        # 从数据库加载分类
        categories = execute_query('SELECT name FROM categories ORDER BY name')
        for category in categories:
            self.category_filter.addItem(category['name'])
    
    def load_passwords(self):
        """
        从数据库加载密码数据
        """
        # 清空表格
        self.password_table.setRowCount(0)
        
        # 从数据库获取密码列表
        query = '''
        SELECT p.id, p.title, p.username, p.encrypted_password, p.url, 
               c.name as category, p.created_at, p.expires_at, p.is_favorite
        FROM passwords p
        LEFT JOIN categories c ON p.category = c.name
        ORDER BY p.is_favorite DESC, p.updated_at DESC
        '''
        
        passwords = execute_query(query)
        
        # 填充表格
        for row_idx, password in enumerate(passwords):
            self.password_table.insertRow(row_idx)
            
            # 设置表格数据
            self.password_table.setItem(row_idx, 0, QTableWidgetItem(password['title']))
            self.password_table.setItem(row_idx, 1, QTableWidgetItem(password['username'] or ''))
            
            # 密码列显示为掩码
            password_item = QTableWidgetItem("••••••••")
            password_item.setData(Qt.ItemDataRole.UserRole, password['encrypted_password'])
            self.password_table.setItem(row_idx, 2, password_item)
            
            self.password_table.setItem(row_idx, 3, QTableWidgetItem(password['url'] or ''))
            self.password_table.setItem(row_idx, 4, QTableWidgetItem(password['category'] or ''))
            
            # 格式化日期
            created_at = password['created_at'] or ''
            self.password_table.setItem(row_idx, 5, QTableWidgetItem(created_at))
            
            expires_at = password['expires_at'] or ''
            expires_item = QTableWidgetItem(expires_at)
            # 如果密码已过期，标记为红色
            if expires_at and datetime.now().date() > datetime.strptime(expires_at, '%Y-%m-%d').date():
                expires_item.setBackground(QColor('#ffcccc'))
            self.password_table.setItem(row_idx, 6, expires_item)
            
            # 收藏状态
            favorite_item = QTableWidgetItem("★" if password['is_favorite'] else "")
            favorite_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.password_table.setItem(row_idx, 7, favorite_item)
            
            # 存储ID供后续使用
            self.password_table.item(row_idx, 0).setData(Qt.ItemDataRole.UserRole, password['id'])
    
    def on_cell_clicked(self, row, column):
        """
        处理表格单元格点击事件
        """
        # 如果点击的是密码列，显示实际密码
        if column == 2:
            password_item = self.password_table.item(row, column)
            encrypted_password = password_item.data(Qt.ItemDataRole.UserRole)
            
            if encrypted_password:
                try:
                    # 解密并显示密码
                    plain_password = PasswordEncryption.decrypt(encrypted_password)
                    password_item.setText(plain_password)
                    
                    # 3秒后恢复为掩码
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(3000, lambda r=row, c=column: 
                                     self.password_table.item(r, c).setText("••••••••") 
                                     if self.password_table.item(r, c) is not None else None)
                except Exception as e:
                    QMessageBox.critical(self, "解密失败", f"无法解密密码: {str(e)}")
    
    def add_password(self):
        """
        添加新密码
        """
        self._edit_password_dialog()
    
    def edit_password(self):
        """
        编辑选中的密码
        """
        selected_rows = self.password_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要编辑的密码")
            return
        
        row = selected_rows[0].row()
        password_id = self.password_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        self._edit_password_dialog(password_id)
    
    def _edit_password_dialog(self, password_id=None):
        """
        编辑密码对话框
        
        Args:
            password_id: 要编辑的密码ID，如果为None则添加新密码
        """
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("添加密码" if password_id is None else "编辑密码")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        # 表单布局
        form_layout = QGridLayout()
        
        # 标题
        form_layout.addWidget(QLabel("标题:"), 0, 0)
        title_edit = QLineEdit()
        form_layout.addWidget(title_edit, 0, 1)
        
        # 用户名
        form_layout.addWidget(QLabel("用户名:"), 1, 0)
        username_edit = QLineEdit()
        form_layout.addWidget(username_edit, 1, 1)
        
        # 密码
        form_layout.addWidget(QLabel("密码:"), 2, 0)
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(password_edit, 2, 1)
        
        # 生成密码按钮
        gen_pass_button = QPushButton("生成")
        gen_pass_button.clicked.connect(lambda: 
            password_edit.setText(PasswordGenerator.generate_password()))
        form_layout.addWidget(gen_pass_button, 2, 2)
        
        # 显示密码复选框
        show_pass_check = QCheckBox("显示密码")
        show_pass_check.stateChanged.connect(lambda state: 
            password_edit.setEchoMode(QLineEdit.EchoMode.Normal if state else QLineEdit.EchoMode.Password))
        form_layout.addWidget(show_pass_check, 3, 1)
        
        # URL
        form_layout.addWidget(QLabel("URL:"), 4, 0)
        url_edit = QLineEdit()
        url_edit.setPlaceholderText("https://example.com")
        form_layout.addWidget(url_edit, 4, 1, 1, 2)
        
        # 分类
        form_layout.addWidget(QLabel("分类:"), 5, 0)
        category_combo = QComboBox()
        # 加载分类
        categories = execute_query('SELECT name FROM categories ORDER BY name')
        for category in categories:
            category_combo.addItem(category['name'])
        form_layout.addWidget(category_combo, 5, 1, 1, 2)
        
        # 过期日期
        form_layout.addWidget(QLabel("过期日期:"), 6, 0)
        expires_edit = QDateEdit()
        expires_edit.setCalendarPopup(True)
        expires_edit.setDate(QDate.currentDate().addDays(365))  # 默认1年后过期
        form_layout.addWidget(expires_edit, 6, 1, 1, 2)
        
        # 笔记
        form_layout.addWidget(QLabel("笔记:"), 7, 0)
        notes_edit = QTextEdit()
        form_layout.addWidget(notes_edit, 7, 1, 3, 2)
        
        # 收藏
        favorite_check = QCheckBox("标记为收藏")
        form_layout.addWidget(favorite_check, 10, 1)
        
        layout.addLayout(form_layout)
        
        # 按钮布局
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_button)
        
        save_button = QPushButton("保存")
        save_button.setDefault(True)
        buttons_layout.addWidget(save_button)
        
        layout.addLayout(buttons_layout)
        
        # 如果是编辑模式，加载现有数据
        if password_id:
            password_data = execute_query(
                'SELECT * FROM passwords WHERE id = ?',
                (password_id,)
            )
            
            if password_data:
                data = password_data[0]
                title_edit.setText(data['title'])
                username_edit.setText(data['username'] or '')
                # 解密并显示现有密码
                try:
                    decrypted_password = PasswordEncryption.decrypt(data['encrypted_password'])
                    password_edit.setText(decrypted_password)
                except Exception as e:
                    QMessageBox.warning(self, "警告", "无法解密现有密码")
                
                url_edit.setText(data['url'] or '')
                
                # 设置分类
                category_index = category_combo.findText(data['category'] or '')
                if category_index >= 0:
                    category_combo.setCurrentIndex(category_index)
                
                # 设置过期日期
                if data['expires_at']:
                    expires_edit.setDate(QDate.fromString(data['expires_at'], 'yyyy-MM-dd'))
                
                notes_edit.setText(data['notes'] or '')
                favorite_check.setChecked(data['is_favorite'])
        
        # 保存按钮点击事件
        def save_password():
            title = title_edit.text().strip()
            password = password_edit.text()
            
            if not title:
                QMessageBox.warning(dialog, "警告", "标题不能为空")
                return
            
            if not password:
                QMessageBox.warning(dialog, "警告", "密码不能为空")
                return
            
            # 加密密码
            encrypted_password = PasswordEncryption.encrypt(password)
            
            # 获取表单数据
            username = username_edit.text().strip()
            url = url_edit.text().strip()
            category = category_combo.currentText()
            expires_at = expires_edit.date().toString('yyyy-MM-dd')
            notes = notes_edit.toPlainText()
            is_favorite = 1 if favorite_check.isChecked() else 0
            
            try:
                if password_id:
                    # 更新密码
                    execute_non_query(
                        '''UPDATE passwords 
                           SET title = ?, username = ?, encrypted_password = ?, url = ?, 
                               category = ?, notes = ?, expires_at = ?, is_favorite = ?, 
                               updated_at = CURRENT_TIMESTAMP 
                           WHERE id = ?''',
                        (title, username, encrypted_password, url, category, 
                         notes, expires_at, is_favorite, password_id)
                    )
                    # 密码已更新，不显示成功提示
                else:
                    # 添加新密码
                    execute_non_query(
                        '''INSERT INTO passwords 
                           (title, username, encrypted_password, url, category, 
                            notes, expires_at, is_favorite) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (title, username, encrypted_password, url, category, 
                         notes, expires_at, is_favorite)
                    )
                    # 密码已添加，不显示成功提示
                
                # 重新加载密码列表
                self.load_passwords()
                dialog.accept()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存密码失败: {str(e)}")
        
        save_button.clicked.connect(save_password)
        
        # 显示对话框
        dialog.exec()
    
    def delete_password(self):
        """
        删除选中的密码
        """
        selected_rows = self.password_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的密码")
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除选中的 {len(selected_rows)} 个密码吗？此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 删除选中的密码
                for row_idx in selected_rows:
                    row = row_idx.row()
                    password_id = self.password_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                    execute_non_query('DELETE FROM passwords WHERE id = ?', (password_id,))
                
                # 密码已删除，不显示成功提示
                # 重新加载密码列表
                self.load_passwords()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除密码失败: {str(e)}")
    
    def show_password_generator(self):
        """
        显示密码生成器对话框
        """
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("密码生成器")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # 密码长度
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("密码长度:"))
        length_spin, ok = QInputDialog.getInt(
            self, "密码长度", "请输入密码长度:", 16, 6, 128, 1
        )
        
        if not ok:
            return
        
        # 密码选项
        options_group = QGroupBox("密码选项")
        options_layout = QVBoxLayout(options_group)
        
        use_uppercase = QCheckBox("包含大写字母 (A-Z)")
        use_uppercase.setChecked(True)
        options_layout.addWidget(use_uppercase)
        
        use_lowercase = QCheckBox("包含小写字母 (a-z)")
        use_lowercase.setChecked(True)
        options_layout.addWidget(use_lowercase)
        
        use_digits = QCheckBox("包含数字 (0-9)")
        use_digits.setChecked(True)
        options_layout.addWidget(use_digits)
        
        use_special = QCheckBox("包含特殊字符 (!@#$%^&*等)")
        use_special.setChecked(True)
        options_layout.addWidget(use_special)
        
        exclude_similar = QCheckBox("排除相似字符 (如 l, 1, O, 0 等)")
        exclude_similar.setChecked(True)
        options_layout.addWidget(exclude_similar)
        
        layout.addWidget(options_group)
        
        # 生成的密码显示
        password_group = QGroupBox("生成的密码")
        password_layout = QVBoxLayout(password_group)
        
        self.generated_password_edit = QLineEdit()
        self.generated_password_edit.setReadOnly(True)
        self.generated_password_edit.setMinimumHeight(40)
        font = QFont()
        font.setPointSize(12)
        self.generated_password_edit.setFont(font)
        password_layout.addWidget(self.generated_password_edit)
        
        # 复制按钮
        copy_button = QPushButton("复制到剪贴板")
        copy_button.clicked.connect(self.copy_to_clipboard)
        password_layout.addWidget(copy_button)
        
        layout.addWidget(password_group)
        
        # 按钮布局
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        regen_button = QPushButton("重新生成")
        regen_button.clicked.connect(lambda: self.generate_and_display_password(
            length_spin, use_uppercase.isChecked(), use_lowercase.isChecked(),
            use_digits.isChecked(), use_special.isChecked(), exclude_similar.isChecked()
        ))
        buttons_layout.addWidget(regen_button)
        
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.close)
        buttons_layout.addWidget(close_button)
        
        layout.addLayout(buttons_layout)
        
        # 初始生成密码
        self.generate_and_display_password(
            length_spin, use_uppercase.isChecked(), use_lowercase.isChecked(),
            use_digits.isChecked(), use_special.isChecked(), exclude_similar.isChecked()
        )
        
        # 显示对话框
        dialog.exec()
    
    def generate_and_display_password(self, length, use_uppercase, use_lowercase,
                                     use_digits, use_special, exclude_similar):
        """
        生成密码并显示
        """
        password = PasswordGenerator.generate_password(
            length, use_uppercase, use_lowercase, use_digits, use_special, exclude_similar
        )
        self.generated_password_edit.setText(password)
    
    def copy_to_clipboard(self):
        """
        复制生成的密码到剪贴板
        """
        password = self.generated_password_edit.text()
        if password:
            clipboard = QApplication.clipboard()
            clipboard.setText(password)
            QMessageBox.information(self, "成功", "密码已复制到剪贴板")
    
    def filter_by_category(self, index):
        """
        按分类筛选密码
        """
        category = self.category_filter.currentText()
        
        # 如果选择"全部"，则加载所有密码
        if category == "全部":
            self.load_passwords()
            return
        
        # 清空表格
        self.password_table.setRowCount(0)
        
        # 查询特定分类的密码
        query = '''
        SELECT p.id, p.title, p.username, p.encrypted_password, p.url, 
               c.name as category, p.created_at, p.expires_at, p.is_favorite
        FROM passwords p
        LEFT JOIN categories c ON p.category = c.name
        WHERE p.category = ?
        ORDER BY p.is_favorite DESC, p.updated_at DESC
        '''
        
        passwords = execute_query(query, (category,))
        
        # 填充表格（与load_passwords方法相同的逻辑）
        for row_idx, password in enumerate(passwords):
            self.password_table.insertRow(row_idx)
            
            # 设置表格数据
            self.password_table.setItem(row_idx, 0, QTableWidgetItem(password['title']))
            self.password_table.setItem(row_idx, 1, QTableWidgetItem(password['username'] or ''))
            
            # 密码列显示为掩码
            password_item = QTableWidgetItem("••••••••")
            password_item.setData(Qt.ItemDataRole.UserRole, password['encrypted_password'])
            self.password_table.setItem(row_idx, 2, password_item)
            
            self.password_table.setItem(row_idx, 3, QTableWidgetItem(password['url'] or ''))
            self.password_table.setItem(row_idx, 4, QTableWidgetItem(password['category'] or ''))
            
            # 格式化日期
            created_at = password['created_at'] or ''
            self.password_table.setItem(row_idx, 5, QTableWidgetItem(created_at))
            
            expires_at = password['expires_at'] or ''
            expires_item = QTableWidgetItem(expires_at)
            # 如果密码已过期，标记为红色
            if expires_at and datetime.now().date() > datetime.strptime(expires_at, '%Y-%m-%d').date():
                expires_item.setBackground(QColor('#ffcccc'))
            self.password_table.setItem(row_idx, 6, expires_item)
            
            # 收藏状态
            favorite_item = QTableWidgetItem("★" if password['is_favorite'] else "")
            favorite_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.password_table.setItem(row_idx, 7, favorite_item)
            
            # 存储ID供后续使用
            self.password_table.item(row_idx, 0).setData(Qt.ItemDataRole.UserRole, password['id'])
    
    def search_passwords(self, search_text):
        """
        搜索密码
        """
        if not search_text.strip():
            self.load_passwords()
            return
        
        # 清空表格
        self.password_table.setRowCount(0)
        
        # 搜索密码
        query = '''
        SELECT p.id, p.title, p.username, p.encrypted_password, p.url, 
               c.name as category, p.created_at, p.expires_at, p.is_favorite
        FROM passwords p
        LEFT JOIN categories c ON p.category = c.name
        WHERE p.title LIKE ? OR p.username LIKE ? OR p.url LIKE ?
        ORDER BY p.is_favorite DESC, p.updated_at DESC
        '''
        
        search_pattern = f'%{search_text}%'
        passwords = execute_query(
            query, (search_pattern, search_pattern, search_pattern)
        )
        
        # 填充表格（与load_passwords方法相同的逻辑）
        for row_idx, password in enumerate(passwords):
            self.password_table.insertRow(row_idx)
            
            # 设置表格数据
            self.password_table.setItem(row_idx, 0, QTableWidgetItem(password['title']))
            self.password_table.setItem(row_idx, 1, QTableWidgetItem(password['username'] or ''))
            
            # 密码列显示为掩码
            password_item = QTableWidgetItem("••••••••")
            password_item.setData(Qt.ItemDataRole.UserRole, password['encrypted_password'])
            self.password_table.setItem(row_idx, 2, password_item)
            
            self.password_table.setItem(row_idx, 3, QTableWidgetItem(password['url'] or ''))
            self.password_table.setItem(row_idx, 4, QTableWidgetItem(password['category'] or ''))
            
            # 格式化日期
            created_at = password['created_at'] or ''
            self.password_table.setItem(row_idx, 5, QTableWidgetItem(created_at))
            
            expires_at = password['expires_at'] or ''
            expires_item = QTableWidgetItem(expires_at)
            # 如果密码已过期，标记为红色
            if expires_at and datetime.now().date() > datetime.strptime(expires_at, '%Y-%m-%d').date():
                expires_item.setBackground(QColor('#ffcccc'))
            self.password_table.setItem(row_idx, 6, expires_item)
            
            # 收藏状态
            favorite_item = QTableWidgetItem("★" if password['is_favorite'] else "")
            favorite_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.password_table.setItem(row_idx, 7, favorite_item)
            
            # 存储ID供后续使用
            self.password_table.item(row_idx, 0).setData(Qt.ItemDataRole.UserRole, password['id'])


# 测试代码（如果直接运行此模块）
if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = PasswordManagerDialog()
    dialog.show()
    sys.exit(app.exec())