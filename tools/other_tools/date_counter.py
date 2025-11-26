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
    QGroupBox, QGridLayout, QDateEdit, QComboBox, QInputDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QIcon

# 导入数据库模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database import execute_query, execute_non_query, create_table, table_exists


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
                # 创建日期记录表
                create_table(
                    "date_records",
                    {
                        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                        "title": "TEXT NOT NULL",
                        "date": "TEXT NOT NULL",
                        "created_at": "TEXT NOT NULL"
                    }
                )
        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"初始化数据库失败: {str(e)}")
    
    def init_ui(self):
        """初始化用户界面"""
        # 主布局
        main_layout = QVBoxLayout()
        
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
        self.dates_table.setColumnCount(3)
        self.dates_table.setHorizontalHeaderLabels(["标题", "日期", "距今天数"])
        
        # 设置表格列宽
        self.dates_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.dates_table.setColumnWidth(0, 150)  # 收窄标题列宽度
        self.dates_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.dates_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
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
            # 保存到数据库
            execute_non_query(
                "INSERT INTO date_records (title, date, created_at) VALUES (?, ?, ?)",
                (title, date_str, created_at)
            )
            
            # 重新加载日期列表
            self.load_dates()
            
            # 清空标题输入
            self.title_edit.clear()
            
            QMessageBox.information(self, "成功", "日期记录已添加")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加日期记录失败: {str(e)}")
    
    def load_dates(self):
        """从数据库加载日期记录"""
        try:
            # 清空表格和下拉框
            self.dates_table.setRowCount(0)
            self.start_date_combo.clear()
            self.end_date_combo.clear()
            
            # 查询所有日期记录
            records = execute_query("SELECT id, title, date FROM date_records ORDER BY date DESC")
            
            # 获取当前日期用于计算天数差
            current_date = datetime.now().date()
            
            # 添加记录到表格和下拉框
            for record in records:
                row_position = self.dates_table.rowCount()
                self.dates_table.insertRow(row_position)
                
                # 设置表格数据
                self.dates_table.setItem(row_position, 0, QTableWidgetItem(record['title']))
                self.dates_table.setItem(row_position, 1, QTableWidgetItem(record['date']))
                
                # 计算并显示距今天数
                record_date = datetime.strptime(record['date'], "%Y-%m-%d").date()
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
                
                # 添加到下拉框
                display_text = f"{record['title']} ({record['date']})"
                self.start_date_combo.addItem(display_text, (record['id'], record['date']))
                self.end_date_combo.addItem(display_text, (record['id'], record['date']))
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
    
    def clear_all_dates(self):
        """清空所有日期记录"""
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
                # 删除所有记录
                execute_non_query("DELETE FROM date_records")
                
                # 重新加载日期列表
                self.load_dates()
                
                # 清空差异结果
                self.diff_result_label.setText("--")
                self.diff_result_label.setStyleSheet("")
                
                QMessageBox.information(self, "成功", "所有日期记录已清空")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清空日期记录失败: {str(e)}")


if __name__ == "__main__":
    # 仅用于测试
    app = QApplication(sys.argv)
    dialog = DateCounterDialog()
    dialog.show()
    sys.exit(app.exec())
