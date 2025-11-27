"""
日期计数工具模块
提供记录多个日期并计算日期之间天数差异的功能
"""
import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QGridLayout, QDateEdit, QComboBox, QInputDialog, QWidget
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QIcon

# 导入数据库模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database import execute_query, execute_non_query, create_table, table_exists
# 导入密码加密模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.other_tools.password_manager import PasswordEncryption


class DateCounterDialog(QDialog):
    """
    日期计数对话框
    支持记录多个日期并为每个日期添加标题，计算日期之间的天数差异
    """
    
    def __init__(self, parent=None):
        """
        初始化日期计数对话框
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        
        # 首先检查并验证主密码
        if not self._check_and_setup_master_password():
            # 如果主密码验证失败，关闭窗口
            self.close()
            return
        
        # 初始化数据库
        self._init_database()
        
        # 从config.json中获取窗口标题（使用工具名称）
        window_title = "日期计数"  # 默认标题
        if parent and hasattr(parent, 'tools'):
            # 查找当前工具的配置
            for tool in parent.tools:
                if hasattr(tool, 'class_name') and tool.class_name == 'DateCounterDialog':
                    window_title = tool.name
                    break
        
        # 设置窗口标题和大小
        self.setWindowTitle(window_title)
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # 初始化UI
        self.init_ui()
        
        # 加载保存的日期数据
        self.load_dates()
        
        # 窗口居中显示
        self.center_window()
        
    def _check_and_setup_master_password(self):
        """
        检查并设置主密码（与password_manager共享）
        如果没有设置主密码，引导用户设置
        如果已设置主密码，要求用户输入验证
        
        Returns:
            bool: 主密码验证是否成功
        """
        try:
            # 检查表是否存在（使用与password_manager相同的表名）
            if not table_exists('master_passwords'):
                # 如果不存在，创建表（使用与password_manager相同的结构）
                columns = {
                    'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                    'salt': 'TEXT NOT NULL',
                    'hashed_password': 'TEXT NOT NULL'
                }
                create_table('master_passwords', columns)
            
            # 检查是否已有主密码（使用与password_manager相同的查询）
            master_password_data = execute_query('SELECT * FROM master_passwords LIMIT 1')
            
            if not master_password_data:
                # 没有主密码，需要设置
                return self._set_master_password()
            else:
                # 有主密码，需要验证
                return self._verify_master_password(master_password_data[0])
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"主密码验证失败: {str(e)}")
            return False
    
    def _set_master_password(self):
        """
        设置主密码（与password_manager共享）
        
        Returns:
            bool: 设置是否成功
        """
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QHBoxLayout, QGridLayout, QCheckBox
        
        # 创建设置主密码对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("设置主密码")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # 添加说明文本
        info_label = QLabel("欢迎使用日期计数工具！\n请设置一个主密码来保护您的日期数据。\n此密码将与密码管理器工具共享，请务必记住！")
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
            salt, password_hash = PasswordEncryption.create_master_password_hash(master_password)
            
            # 保存到数据库
            try:
                execute_non_query(
                    'INSERT INTO master_passwords (salt, hashed_password) VALUES (?, ?)',
                    (salt, password_hash)
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
        验证主密码（与password_manager共享）
        
        Args:
            master_password_data: 主密码数据字典
            
        Returns:
            bool: 验证是否成功
        """
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QHBoxLayout, QCheckBox
        
        # 获取盐值和哈希密码
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
            info_text = f"请输入主密码来访问您的日期记录。\n剩余尝试次数: {remaining_attempts}"
            if remaining_attempts < 5:
                info_text += "\n请注意：连续输入错误5次将清空所有数据！"
            
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
                    info_label.setText(f"请输入主密码来访问您的日期记录。\n剩余尝试次数: {remaining_attempts}\n请注意：连续输入错误5次将清空所有数据！")
                    
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
                # 用户取消或关闭窗口，直接返回False
                return False
        
        # 所有尝试都失败，清空所有日期数据
        self._clear_all_dates()
        QMessageBox.critical(self, "验证失败", "主密码连续验证失败5次，所有日期数据已清空。应用将关闭。")
        self.reject()  # 确保对话框被拒绝
        return False
    
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
    
    def _init_database(self):
        """初始化数据库，创建日期记录表（如果不存在）"""
        try:
            # 检查日期表是否存在
            if not table_exists("date_records"):
                # 创建日期记录表，包含排序字段
                create_table(
                    "date_records",
                    {
                        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                        "title": "TEXT NOT NULL",  # 加密后的标题
                        "date": "TEXT NOT NULL",   # 加密后的日期
                        "created_at": "TEXT NOT NULL",
                        "order_index": "INTEGER DEFAULT 0"
                    }
                )
        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"初始化数据库失败: {str(e)}")
    
    def _clear_all_dates(self):
        """
        清空所有日期数据
        """
        try:
            # 删除所有日期记录
            execute_non_query('DELETE FROM date_records')
            # 重置自增ID
            execute_non_query('DELETE FROM sqlite_sequence WHERE name="date_records"')
        except Exception as e:
            print(f"清空日期数据时出错: {str(e)}")
    
    def init_ui(self):
        """初始化用户界面"""
        # 主布局
        main_layout = QVBoxLayout()
        
        # 存储行ID映射，用于编辑和删除操作
        self.row_id_map = {}
        
        # 创建添加日期的分组框
        add_date_group = QGroupBox("添加日期记录")
        add_date_layout = QGridLayout()
        
        # 日期标题
        add_date_layout.addWidget(QLabel("标题:"), 0, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("输入日期标题")
        add_date_layout.addWidget(self.title_edit, 0, 1, 1, 3)
        
        # 日期选择
        add_date_layout.addWidget(QLabel("日期:"), 1, 0)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        add_date_layout.addWidget(self.date_edit, 1, 1)
        
        # 添加按钮
        self.add_button = QPushButton("添加日期")
        self.add_button.clicked.connect(self.add_date)
        add_date_layout.addWidget(self.add_button, 1, 2)
        
        # 清空所有按钮
        self.clear_all_button = QPushButton("清空所有")
        self.clear_all_button.clicked.connect(self.clear_all_dates)
        add_date_layout.addWidget(self.clear_all_button, 1, 3)
        
        # 设置列拉伸
        add_date_layout.setColumnStretch(1, 1)
        
        add_date_group.setLayout(add_date_layout)
        main_layout.addWidget(add_date_group)
        
        # 创建日期列表表格
        self.dates_table = QTableWidget()
        self.dates_table.setColumnCount(4)
        self.dates_table.setHorizontalHeaderLabels(["标题", "日期", "距今天数", "操作"])
        
        # 设置表格列宽
        self.dates_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.dates_table.setColumnWidth(0, 150)  # 收窄标题列宽度
        self.dates_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.dates_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.dates_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # 设置单元格双击事件
        self.dates_table.cellDoubleClicked.connect(self.edit_cell)
        
        main_layout.addWidget(self.dates_table)
        
        # 创建计算差异的分组框
        calc_diff_group = QGroupBox("计算日期差异")
        calc_diff_layout = QGridLayout()
        
        # 起始日期选择
        calc_diff_layout.addWidget(QLabel("起始日期:"), 0, 0)
        self.start_date_combo = QComboBox()
        calc_diff_layout.addWidget(self.start_date_combo, 0, 1)
        
        # 结束日期选择
        calc_diff_layout.addWidget(QLabel("结束日期:"), 0, 2)
        self.end_date_combo = QComboBox()
        calc_diff_layout.addWidget(self.end_date_combo, 0, 3)
        
        # 计算按钮
        self.calc_diff_button = QPushButton("计算差异")
        self.calc_diff_button.clicked.connect(self.calculate_difference)
        calc_diff_layout.addWidget(self.calc_diff_button, 0, 4)
        
        # 差异结果
        calc_diff_layout.addWidget(QLabel("差异天数:"), 1, 0)
        self.diff_result_label = QLabel("--")
        self.diff_result_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        calc_diff_layout.addWidget(self.diff_result_label, 1, 1, 1, 4)
        
        # 设置列拉伸
        calc_diff_layout.setColumnStretch(1, 1)
        calc_diff_layout.setColumnStretch(3, 1)
        
        calc_diff_group.setLayout(calc_diff_layout)
        main_layout.addWidget(calc_diff_group)
        
        # 设置主布局
        self.setLayout(main_layout)
    
    def add_date(self):
        """添加新的日期记录"""
        # 获取标题和日期
        title = self.title_edit.text().strip()
        date = self.date_edit.date()
        
        # 验证输入
        if not title:
            QMessageBox.warning(self, "输入错误", "请输入日期标题")
            return
        
        # 格式化日期
        date_str = date.toString("yyyy-MM-dd")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # 加密标题和日期
            encrypted_title = PasswordEncryption.encrypt(title)
            encrypted_date = PasswordEncryption.encrypt(date_str)
            
            # 获取当前最大排序索引
            max_order = execute_query("SELECT COALESCE(MAX(order_index), -1) as max_order FROM date_records")[0]['max_order']
            
            # 保存到数据库，设置排序索引为最大值+1
            execute_non_query(
                "INSERT INTO date_records (title, date, created_at, order_index) VALUES (?, ?, ?, ?)",
                (encrypted_title, encrypted_date, created_at, max_order + 1)
            )
            
            # 重新加载日期列表
            self.load_dates()
            
            # 清空标题输入
            self.title_edit.clear()
            
            QMessageBox.information(self, "成功", "日期记录已添加")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加日期记录失败: {str(e)}")
    
    def load_dates(self):
        """
        从数据库加载日期记录
        """
        try:
            # 清空表格和下拉框
            self.dates_table.setRowCount(0)
            self.start_date_combo.clear()
            self.end_date_combo.clear()
            
            # 查询所有日期记录，按照排序字段排序
            records = execute_query("SELECT id, title, date FROM date_records ORDER BY order_index ASC")
            
            # 获取当前日期用于计算天数差
            current_date = datetime.now().date()
            
            # 添加记录到表格和下拉框
            for record in records:
                row_position = self.dates_table.rowCount()
                self.dates_table.insertRow(row_position)
                
                try:
                    # 解密标题和日期
                    decrypted_title = PasswordEncryption.decrypt(record['title'])
                    decrypted_date = PasswordEncryption.decrypt(record['date'])
                except Exception as decrypt_error:
                    QMessageBox.warning(self, "解密错误", f"无法解密记录ID {record['id']}: {str(decrypt_error)}")
                    decrypted_title = "[解密失败]"
                    decrypted_date = "[解密失败]"
                
                # 设置表格数据
                self.dates_table.setItem(row_position, 0, QTableWidgetItem(decrypted_title))
                self.dates_table.setItem(row_position, 1, QTableWidgetItem(decrypted_date))
                
                # 计算并显示距今天数（只有在解密成功时）
                if decrypted_date != "[解密失败]":
                    try:
                        record_date = datetime.strptime(decrypted_date, "%Y-%m-%d").date()
                        days_diff = (current_date - record_date).days
                        diff_item = QTableWidgetItem(str(days_diff))
                        
                        # 根据正负设置颜色
                        if days_diff < 0:
                            diff_item.setForeground(QColor("blue"))  # 未来日期
                        elif days_diff > 0:
                            diff_item.setForeground(QColor("red"))  # 过去日期
                        else:
                            diff_item.setForeground(QColor("green"))  # 今天
                        
                        self.dates_table.setItem(row_position, 2, diff_item)
                    except ValueError:
                        self.dates_table.setItem(row_position, 2, QTableWidgetItem("--"))
                else:
                    self.dates_table.setItem(row_position, 2, QTableWidgetItem("--"))
                
                # 添加操作按钮
                self._add_action_buttons(row_position, record['id'])
                
                # 添加到下拉框
                display_text = f"{decrypted_title} ({decrypted_date})"
                # 存储解密后的日期用于计算
                self.start_date_combo.addItem(display_text, (record['id'], decrypted_date))
                self.end_date_combo.addItem(display_text, (record['id'], decrypted_date))
                
                # 存储行ID映射
                self.row_id_map[row_position] = record['id']
            
            # 所有行添加完成后，更新按钮状态
            self._update_button_states()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载日期记录失败: {str(e)}")
    
    def calculate_difference(self):
        """计算两个日期之间的差异"""
        # 获取选择的日期
        start_index = self.start_date_combo.currentIndex()
        end_index = self.end_date_combo.currentIndex()
        
        # 验证选择
        if start_index < 0 or end_index < 0:
            QMessageBox.warning(self, "选择错误", "请选择起始日期和结束日期")
            return
        
        # 获取日期数据
        start_date_data = self.start_date_combo.currentData()
        end_date_data = self.end_date_combo.currentData()
        
        # 解析日期
        start_date = datetime.strptime(start_date_data[1], "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_data[1], "%Y-%m-%d").date()
        
        # 计算差异
        days_diff = (end_date - start_date).days
        
        # 显示结果
        self.diff_result_label.setText(f"{days_diff} 天")
        
        # 根据正负设置颜色
        if days_diff > 0:
            self.diff_result_label.setStyleSheet("color: green;")
        elif days_diff < 0:
            self.diff_result_label.setStyleSheet("color: red;")
        else:
            self.diff_result_label.setStyleSheet("color: black;")
    
    def _add_action_buttons(self, row, record_id):
        """
        为指定行添加操作按钮
        
        Args:
            row: 行索引
            record_id: 记录ID
        """
        # 创建按钮容器
        button_widget = QWidget()
        layout = QHBoxLayout(button_widget)
        layout.setContentsMargins(2, 2, 2, 2)
        
        # 上移按钮
        up_button = QPushButton("↑")
        up_button.setFixedSize(30, 25)
        up_button.clicked.connect(lambda checked, r=row: self.move_item_up(r))
        up_button.setEnabled(row > 0)  # 第一行不能上移
        layout.addWidget(up_button)
        
        # 下移按钮 - 先启用，后续在update_button_states中正确设置
        down_button = QPushButton("↓")
        down_button.setFixedSize(30, 25)
        down_button.clicked.connect(lambda checked, r=row: self.move_item_down(r))
        down_button.setObjectName(f"down_button_{row}")  # 设置对象名以便后续查找
        layout.addWidget(down_button)
        
        # 删除按钮
        delete_button = QPushButton("删除")
        delete_button.setFixedSize(50, 25)
        delete_button.clicked.connect(lambda checked, r=row, rid=record_id: self.delete_item(r, rid))
        layout.addWidget(delete_button)
        
        # 设置单元格
        self.dates_table.setCellWidget(row, 3, button_widget)
    
    def move_item_up(self, row):
        """
        上移条目
        
        Args:
            row: 当前行索引
        """
        if row > 0:
            # 获取当前行和上一行的ID
            current_id = self.row_id_map[row]
            prev_id = self.row_id_map[row - 1]
            
            # 更新数据库中的排序（交换排序索引）
            try:
                # 获取两行的排序索引
                current_record = execute_query("SELECT order_index FROM date_records WHERE id = ?", (current_id,))[0]
                prev_record = execute_query("SELECT order_index FROM date_records WHERE id = ?", (prev_id,))[0]
                
                # 交换排序索引
                execute_non_query(
                    "UPDATE date_records SET order_index = ? WHERE id = ?",
                    (current_record['order_index'], prev_id)
                )
                execute_non_query(
                    "UPDATE date_records SET order_index = ? WHERE id = ?",
                    (prev_record['order_index'], current_id)
                )
                
                # 重新加载数据（包括解密显示）
                self.load_dates()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"排序失败: {str(e)}")
    
    def _update_button_states(self):
        """
        更新所有按钮的启用状态
        在表格完全加载后调用此方法确保按钮状态正确
        """
        total_rows = self.dates_table.rowCount()
        for row in range(total_rows):
            # 获取操作按钮容器
            button_widget = self.dates_table.cellWidget(row, 3)
            if button_widget:
                # 获取所有按钮
                buttons = button_widget.findChildren(QPushButton)
                for button in buttons:
                    if button.text() == "↑":
                        # 设置上移按钮状态
                        button.setEnabled(row > 0)
                    elif button.text() == "↓":
                        # 设置下移按钮状态
                        button.setEnabled(row < total_rows - 1)
    
    def move_item_down(self, row):
        """
        下移条目
        
        Args:
            row: 当前行索引
        """
        total_rows = self.dates_table.rowCount()
        if row < total_rows - 1:
            # 获取当前行和下一行的ID
            current_id = self.row_id_map[row]
            next_id = self.row_id_map[row + 1]
            
            # 更新数据库中的排序（交换排序索引）
            try:
                # 获取两行的排序索引
                current_record = execute_query("SELECT order_index FROM date_records WHERE id = ?", (current_id,))[0]
                next_record = execute_query("SELECT order_index FROM date_records WHERE id = ?", (next_id,))[0]
                
                # 交换排序索引
                execute_non_query(
                    "UPDATE date_records SET order_index = ? WHERE id = ?",
                    (current_record['order_index'], next_id)
                )
                execute_non_query(
                    "UPDATE date_records SET order_index = ? WHERE id = ?",
                    (next_record['order_index'], current_id)
                )
                
                # 重新加载数据（包括解密显示）
                self.load_dates()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"排序失败: {str(e)}")
    
    def delete_item(self, row, record_id):
        """
        删除指定条目（加密数据）
        
        Args:
            row: 行索引
            record_id: 记录ID
        """
        # 获取标题用于确认消息
        title = self.dates_table.item(row, 0).text()
        
        # 确认对话框
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除 '{title}' 吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 从数据库删除加密的记录
                execute_non_query(
                    "DELETE FROM date_records WHERE id = ?",
                    (record_id,)
                )
                
                # 重新加载数据（包括解密显示）
                self.load_dates()
                
                # 清空差异结果
                self.diff_result_label.setText("--")
                self.diff_result_label.setStyleSheet("")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除条目失败: {str(e)}")
    
    def edit_cell(self, row, column):
        """
        处理单元格双击事件，实现编辑功能
        
        Args:
            row: 行索引
            column: 列索引
        """
        # 只允许编辑标题和日期列
        if column < 2 and row in self.row_id_map:
            record_id = self.row_id_map[row]
            current_value = self.dates_table.item(row, column).text()
            
            if column == 0:  # 编辑标题
                new_title, ok = QInputDialog.getText(self, "编辑标题", "请输入新的标题:", text=current_value)
                if ok and new_title.strip():
                    try:
                        # 加密新标题
                        encrypted_title = PasswordEncryption.encrypt(new_title.strip())
                        
                        # 更新数据库
                        execute_non_query(
                            "UPDATE date_records SET title = ? WHERE id = ?",
                            (encrypted_title, record_id)
                        )
                        
                        # 更新表格
                        self.dates_table.item(row, column).setText(new_title.strip())
                        
                        # 重新加载数据以更新下拉框和重新计算天数差
                        self.load_dates()
                        
                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"更新标题失败: {str(e)}")
            
            elif column == 1:  # 编辑日期
                try:
                    # 解析当前日期（如果不是解密失败的情况）
                    if current_value != "[解密失败]":
                        current_date = datetime.strptime(current_value, "%Y-%m-%d").date()
                        qdate = QDate(current_date.year, current_date.month, current_date.day)
                    else:
                        # 使用当前日期作为默认值
                        today = date.today()
                        qdate = QDate(today.year, today.month, today.day)
                    
                    # 创建日期编辑对话框
                    from PyQt6.QtWidgets import QCalendarWidget, QDialog, QVBoxLayout, QPushButton, QHBoxLayout
                    
                    class DateEditDialog(QDialog):
                        def __init__(self, parent, initial_date):
                            super().__init__(parent)
                            self.setWindowTitle("选择日期")
                            layout = QVBoxLayout()
                            
                            self.calendar = QCalendarWidget()
                            self.calendar.setSelectedDate(initial_date)
                            layout.addWidget(self.calendar)
                            
                            button_layout = QHBoxLayout()
                            self.ok_button = QPushButton("确定")
                            self.cancel_button = QPushButton("取消")
                            
                            self.ok_button.clicked.connect(self.accept)
                            self.cancel_button.clicked.connect(self.reject)
                            
                            button_layout.addWidget(self.ok_button)
                            button_layout.addWidget(self.cancel_button)
                            layout.addLayout(button_layout)
                            
                            self.setLayout(layout)
                            self.resize(300, 300)
                        
                        def get_selected_date(self):
                            return self.calendar.selectedDate()
                    
                    # 显示日期选择对话框
                    dialog = DateEditDialog(self, qdate)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        new_date = dialog.get_selected_date()
                        date_str = new_date.toString("yyyy-MM-dd")
                        
                        # 加密新日期
                        encrypted_date = PasswordEncryption.encrypt(date_str)
                        
                        # 更新数据库
                        execute_non_query(
                            "UPDATE date_records SET date = ? WHERE id = ?",
                            (encrypted_date, record_id)
                        )
                        
                        # 更新表格
                        self.dates_table.item(row, column).setText(date_str)
                        
                        # 重新加载数据以更新下拉框和重新计算天数差
                        self.load_dates()
                        
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"更新日期失败: {str(e)}")
    
    def clear_all_dates(self):
        """清空所有日期记录（加密数据）"""
        # 确认对话框
        reply = QMessageBox.question(
            self, 
            "确认清空", 
            "确定要清空所有日期记录吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 删除所有加密的记录
                execute_non_query("DELETE FROM date_records")
                
                # 重新加载日期列表（包括解密显示）
                self.load_dates()
                
                # 清空差异结果
                self.diff_result_label.setText("--")
                self.diff_result_label.setStyleSheet("")
                
                QMessageBox.information(self, "成功", "所有日期记录已清空")
                # 清空行ID映射
                self.row_id_map.clear()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清空日期记录失败: {str(e)}")


if __name__ == "__main__":
    # 仅用于测试
    app = QApplication(sys.argv)
    dialog = DateCounterDialog()
    dialog.show()
    sys.exit(app.exec())
