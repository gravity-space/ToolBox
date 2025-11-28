import os
import re
import datetime
import sys
from typing import List
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox, QFileDialog, QLineEdit, QHBoxLayout, QTextEdit, QCheckBox, QComboBox, QSizePolicy, QStyledItemDelegate, QStyleOptionViewItem, QStyle, QApplication, QWidget, QAbstractItemView, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt, QModelIndex, QRect, pyqtSignal, QEvent, QSize
from PyQt6.QtGui import QPainter, QColor

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# 确保能够导入database模块
from database import execute_query, execute_non_query, create_table, table_exists


class SearchHistoryDelegate(QStyledItemDelegate):
    """自定义委托类，用于显示搜索历史记录"""
    
    def paint(self, painter, option, index):
        # 绘制正常的文本内容
        super().paint(painter, option, index)
    
    def sizeHint(self, option, index):
        return super().sizeHint(option, index)


    def _get_search_history_database() -> List[str]:
        """
        获取搜索历史记录
        
        Returns:
            List[str]: 搜索历史记录列表
        """
        # 确保表存在
        if not table_exists('search_history'):
            create_table('search_history', {
                'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                'search_text': 'TEXT NOT NULL',
                'search_time': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            })
        
        # 查询最近的搜索记录（最多20条）
        query = "SELECT search_text FROM search_history ORDER BY search_time DESC LIMIT 20"
        results = execute_query(query)
        return [row['search_text'] for row in results]


    def _delete_search_history_database(search_text: str) -> None:
        """
        删除指定的搜索历史记录
        
        Args:
            search_text: 要删除的搜索文本
        """
        if table_exists('search_history'):
            query = "DELETE FROM search_history WHERE search_text = ?"
            execute_non_query(query, (search_text,))


    def _save_search_history_database(search_text: str) -> None:
        """
        保存搜索历史记录
        
        Args:
            search_text: 要保存的搜索文本
        """
        # 确保表存在
        if not table_exists('search_history'):
            create_table('search_history', {
                'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                'search_text': 'TEXT NOT NULL',
                'search_time': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            })
        
        # 先删除可能已存在的相同记录
        delete_query = "DELETE FROM search_history WHERE search_text = ?"
        execute_non_query(delete_query, (search_text,))
        
        # 插入新记录
        insert_query = "INSERT INTO search_history (search_text) VALUES (?);"
        execute_non_query(insert_query, (search_text,))


class HistoryManagerDialog(QDialog):
    """历史记录管理窗口"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("历史记录管理")
        self.resize(1000, 800)
        self.init_ui()
        self.load_history_data()
        
    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("搜索历史记录")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["搜索内容", "使用次数", "最后使用时间"])
        # 设置列宽
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        # 允许选择多行
        self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        main_layout.addWidget(self.history_table)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        delete_selected_btn = QPushButton("删除选中")
        delete_selected_btn.clicked.connect(self.delete_selected_history)
        
        delete_all_btn = QPushButton("清空所有")
        delete_all_btn.clicked.connect(self.delete_all_history)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_history_data)
        
        button_layout.addWidget(delete_selected_btn)
        button_layout.addWidget(delete_all_btn)
        button_layout.addWidget(refresh_btn)
        main_layout.addLayout(button_layout)
    
    def load_history_data(self):
        """加载历史记录数据到表格"""
        # 清空表格
        self.history_table.setRowCount(0)
        
        # 从数据库加载历史记录
        query = "SELECT search_text, count, last_used FROM search_history ORDER BY last_used DESC"
        try:
            results = execute_query(query)
            
            # 添加数据到表格
            for row_idx, row in enumerate(results):
                self.history_table.insertRow(row_idx)
                
                # 搜索内容
                text_item = QTableWidgetItem(row['search_text'])
                text_item.setFlags(text_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.history_table.setItem(row_idx, 0, text_item)
                
                # 使用次数
                count_item = QTableWidgetItem(str(row['count']))
                count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.history_table.setItem(row_idx, 1, count_item)
                
                # 最后使用时间
                time_item = QTableWidgetItem(row['last_used'])
                time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.history_table.setItem(row_idx, 2, time_item)
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载历史记录失败: {str(e)}")
    
    def delete_selected_history(self):
        """删除选中的历史记录"""
        selected_rows = set(item.row() for item in self.history_table.selectedItems())
        
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要删除的历史记录")
            return
        
        try:
            deleted_count = 0
            for row_idx in sorted(selected_rows, reverse=True):
                search_text = self.history_table.item(row_idx, 0).text()
                # 删除数据库中的记录
                query = "DELETE FROM search_history WHERE search_text = ?"
                execute_non_query(query, (search_text,))
                # 从表格中删除行
                self.history_table.removeRow(row_idx)
                deleted_count += 1        
            
            # 如果父窗口存在，刷新父窗口的搜索历史
            if self.parent and hasattr(self.parent, 'load_search_history'):
                self.parent.load_search_history()
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"删除历史记录失败: {str(e)}")
    
    def delete_all_history(self):
        """清空所有历史记录"""
        # 确认删除
        reply = QMessageBox.question(self, "确认删除", "确定要清空所有历史记录吗？此操作不可恢复！",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # 删除数据库中的所有记录
            query = "DELETE FROM search_history"
            execute_non_query(query)
            
            # 清空表格
            self.history_table.setRowCount(0)
            
            QMessageBox.information(self, "成功", "所有历史记录已清空")
            
            # 如果父窗口存在，刷新父窗口的搜索历史
            if self.parent and hasattr(self.parent, 'load_search_history'):
                self.parent.load_search_history()
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"清空历史记录失败: {str(e)}")

class SearchReplaceDialog(QDialog):
    """文件夹内搜索替换工具对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_path = ""  # 初始文件夹路径为空
        self.preview_results = []  # 存储预览结果
        # 从config.json中获取窗口标题（使用工具名称）
        if parent and hasattr(parent, 'tools'):
            # 查找当前工具的配置
            for tool in parent.tools:
                if tool.class_name == 'SearchReplaceDialog':
                    self.setWindowTitle(tool.name)
                    break
        # 初始化数据库
        self.init_database()
        self.init_ui()
    
    def init_database(self):
        """初始化搜索历史记录表"""
        # 检查并创建搜索历史表
        if not table_exists('search_history'):
            columns = {
                'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                'search_text': 'TEXT NOT NULL',
                'count': 'INTEGER DEFAULT 1',
                'last_used': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            create_table('search_history', columns)
    
    def load_search_history(self):
        """加载搜索历史到下拉框"""
        # 从数据库获取最近使用的搜索词（按使用次数和最后使用时间排序）
        query = "SELECT search_text FROM search_history ORDER BY count DESC, last_used DESC LIMIT 20"
        try:
            results = execute_query(query)
            # 清空下拉框中的历史记录（保留当前输入）
            current_text = self.search_edit.currentText()
            self.search_edit.clear()
            # 添加历史记录（去重）
            added_texts = set()
            has_history = False
            for row in results:
                search_text = row['search_text']
                if search_text not in added_texts:
                    self.search_edit.addItem(search_text)
                    added_texts.add(search_text)
                    has_history = True
            # 当没有历史记录时，添加一个不可选的提示项
            if not has_history:
                placeholder_index = self.search_edit.addItem("(无历史记录)")
                self.search_edit.model().item(placeholder_index).setEnabled(False)
            # 恢复当前输入（如果有），否则保持不选中任何项
            if current_text:
                self.search_edit.setCurrentText(current_text)
            else:
                # 确保不自动选中任何历史记录项
                self.search_edit.setCurrentIndex(-1)
        except Exception as e:
            print(f"加载搜索历史时出错: {e}")
    
    def save_search_history(self, search_text):
        """保存搜索词到数据库"""
        if not search_text.strip():
            return
        
        try:
            # 检查是否已存在该搜索词
            query = "SELECT id, count FROM search_history WHERE search_text = ?"
            result = execute_query(query, (search_text,))
            
            if result:
                # 更新现有记录
                search_id = result[0]['id']
                new_count = result[0]['count'] + 1
                update_query = "UPDATE search_history SET count = ?, last_used = ? WHERE id = ?"
                execute_non_query(update_query, (new_count, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), search_id))
            else:
                # 插入新记录
                insert_query = "INSERT INTO search_history (search_text, last_used) VALUES (?, ?)"
                execute_non_query(insert_query, (search_text, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        except Exception as e:
            print(f"保存搜索历史时出错: {e}")
    
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
    
    def init_ui(self):
        # 设置窗口属性
        # 如果未在构造函数中设置窗口标题，则使用默认标题
        if not self.windowTitle():
            self.setWindowTitle("窗口")
        self.resize(700, 500)  # 只设置大小，不设置位置
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 文件夹选择部分
        folder_layout = QHBoxLayout()
        folder_label = QLabel("选择文件夹:")
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setReadOnly(True)
        browse_btn = QPushButton("选择文件夹")
        browse_btn.clicked.connect(self.select_folder)
        
        # 添加打开文件夹按钮
        open_folder_btn = QPushButton("打开文件夹")
        open_folder_btn.clicked.connect(self.open_folder)
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_path_edit)
        folder_layout.addWidget(browse_btn)
        folder_layout.addWidget(open_folder_btn)
        main_layout.addLayout(folder_layout)
        
        # 文件类型筛选
        file_type_layout = QHBoxLayout()
        file_type_label = QLabel("文件类型:")
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItems(["所有文件 (*.*)", "文本文件 (*.txt)", "Python文件 (*.py)", "JSON文件 (*.json)", "HTML文件 (*.html;*.htm)", "自定义..."])
        self.custom_type_edit = QLineEdit()
        self.custom_type_edit.setPlaceholderText("例如: *.txt;*.md")
        self.custom_type_edit.setEnabled(False)
        self.file_type_combo.currentTextChanged.connect(self.on_file_type_changed)
        
        file_type_layout.addWidget(file_type_label)
        file_type_layout.addWidget(self.file_type_combo)
        file_type_layout.addWidget(self.custom_type_edit)
        main_layout.addLayout(file_type_layout)
        
        # 搜索替换输入
        search_layout = QHBoxLayout()
        search_label = QLabel("查找内容:")
        self.search_edit = QComboBox()
        self.search_edit.setEditable(True)  # 允许输入新内容
        self.search_edit.setMinimumWidth(400)  # 增加最小宽度
        self.search_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # 设置扩展策略
        # 设置样式表以防止hover时边框闪烁
        self.search_edit.setStyleSheet("""
            QComboBox {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                padding: 2px 5px;
            }
            QComboBox:hover {
                border: 1px solid #CCCCCC;  /* 保持与正常状态相同 */
            }
            QComboBox:focus {
                border: 1px solid #66A8FF;
                outline: none;
            }
        """)
        
        # 应用自定义委托
        self.delegate = SearchHistoryDelegate()
        self.search_edit.setItemDelegate(self.delegate)
        
        # 加载历史搜索词
        self.load_search_history()
        # 当下拉框选择变化时，更新输入
        self.search_edit.currentTextChanged.connect(self.on_search_text_changed)
        
        # 添加历史记录管理按钮
        self.history_manager_btn = QPushButton("历史记录管理")
        self.history_manager_btn.clicked.connect(self.open_history_manager)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit, 1)  # 添加伸展因子
        search_layout.addWidget(self.history_manager_btn)
        main_layout.addLayout(search_layout)
        
        replace_layout = QHBoxLayout()
        replace_label = QLabel("替换为:")
        self.replace_edit = QLineEdit()
        
        replace_layout.addWidget(replace_label)
        replace_layout.addWidget(self.replace_edit)
        main_layout.addLayout(replace_layout)
        
        # 选项设置
        options_layout = QHBoxLayout()
        self.case_sensitive_check = QCheckBox("区分大小写")
        self.use_regex_check = QCheckBox("使用正则表达式")
        self.include_subfolders_check = QCheckBox("包含子文件夹")
        self.include_subfolders_check.setChecked(True)
        
        options_layout.addWidget(self.case_sensitive_check)
        options_layout.addWidget(self.use_regex_check)
        options_layout.addWidget(self.include_subfolders_check)
        main_layout.addLayout(options_layout)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        preview_btn = QPushButton("搜索")
        preview_btn.clicked.connect(self.preview_replace)
        replace_btn = QPushButton("替换")
        replace_btn.clicked.connect(self.start_replace)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        
        button_layout.addWidget(preview_btn)
        button_layout.addWidget(replace_btn)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)
        
        # 日志输出区域
        log_label = QLabel("操作日志:")
        main_layout.addWidget(log_label)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        main_layout.addWidget(self.log_edit)
        
        # 存储预览结果，用于后续替换
        self.preview_results = []
        
        # 将窗口设置在屏幕中央
        self.center_window()
    
    def open_history_manager(self):
        """打开历史记录管理窗口"""
        history_dialog = HistoryManagerDialog(self)
        history_dialog.exec()
    
    def on_search_text_changed(self, text):
        """当搜索文本变化时的处理"""
        # 当用户从下拉框选择或手动输入完成后，可以在这里添加逻辑
        # 实际保存应该在搜索操作执行时进行
    

    
    def on_file_type_changed(self, text):
        """文件类型变化时的处理"""
        self.custom_type_edit.setEnabled(text == "自定义...")
    
    def select_folder(self):
        """选择文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹", "")
        if folder_path:
            self.folder_path = folder_path
            self.folder_path_edit.setText(folder_path)
            self.log_edit.append(f"已选择文件夹: {folder_path}")
    
    def open_folder(self):
        """打开选中的文件夹"""
        if hasattr(self, 'folder_path') and os.path.isdir(self.folder_path):
            try:
                if sys.platform == 'win32':
                    os.startfile(self.folder_path)
                elif sys.platform == 'darwin':  # macOS
                    os.system(f'open "{self.folder_path}"')
                else:  # Linux等其他系统
                    os.system(f'xdg-open "{self.folder_path}"')
            except Exception as e:
                self.log_edit.append(f"无法打开文件夹: {str(e)}")
        else:
            self.log_edit.append("请先选择一个有效的文件夹")
    
    def get_file_patterns(self):
        """获取文件匹配模式"""
        selected_type = self.file_type_combo.currentText()
        if selected_type == "自定义...":
            custom_pattern = self.custom_type_edit.text().strip()
            if custom_pattern:
                return [p.strip() for p in custom_pattern.split(';')]
            else:
                return ["*"]
        elif selected_type == "所有文件 (*.*)":
            return ["*"]
        else:
            # 从下拉选项中提取通配符
            pattern_start = selected_type.find('(') + 1
            pattern_end = selected_type.find(')')
            if pattern_start > 0 and pattern_end > pattern_start:
                pattern_text = selected_type[pattern_start:pattern_end]
                return [p.strip() for p in pattern_text.split(';')]
            return ["*"]
    
    def matches_file_pattern(self, filename, patterns):
        """检查文件是否匹配任一模式"""
        for pattern in patterns:
            # 简单的通配符匹配
            # 将 * 转换为 .* 用于正则匹配
            regex_pattern = pattern.replace('.', '\\.').replace('*', '.*')
            if re.match(f"^{regex_pattern}$", filename):
                return True
        return False
    
    def get_files_to_process(self):
        """获取要处理的文件列表"""
        if not self.folder_path:
            return []
        
        files_to_process = []
        file_patterns = self.get_file_patterns()
        
        try:
            if self.include_subfolders_check.isChecked():
                # 遍历所有子文件夹
                for root, _, files in os.walk(self.folder_path):
                    for filename in files:
                        if self.matches_file_pattern(filename, file_patterns):
                            files_to_process.append(os.path.join(root, filename))
            else:
                # 只处理当前文件夹
                for filename in os.listdir(self.folder_path):
                    file_path = os.path.join(self.folder_path, filename)
                    if os.path.isfile(file_path) and self.matches_file_pattern(filename, file_patterns):
                        files_to_process.append(file_path)
        except Exception as e:
            self.log_edit.append(f"获取文件列表时出错: {str(e)}")
        
        return files_to_process
    
    def parse_search_keywords(self, search_input):
        """解析搜索关键词，支持空格或逗号分隔"""
        # 首先用逗号分隔
        keywords = [k.strip() for k in search_input.split(',') if k.strip()]
        # 如果没有逗号，则用空格分隔
        if len(keywords) == 1:
            keywords = [k.strip() for k in keywords[0].split() if k.strip()]
        return keywords
    
    def preview_replace(self):
        """搜索替换结果"""
        # 验证输入
        if not self.folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹！")
            return

        search_input = self.search_edit.currentText()
        if not search_input:
            QMessageBox.warning(self, "警告", "请输入查找内容！")
            return

        # 保存搜索词到数据库
        self.save_search_history(search_input)
        # 重新加载搜索历史，更新下拉框
        self.load_search_history()
        
        # 解析多关键词
        search_keywords = self.parse_search_keywords(search_input)
        
        self.log_edit.clear()
        self.log_edit.append("开始搜索替换结果...")
        self.log_edit.append(f"搜索关键词: {', '.join(search_keywords)}")
        self.preview_results = []
        
        files_to_process = self.get_files_to_process()
        self.log_edit.append(f"找到 {len(files_to_process)} 个文件待处理")
        
        total_matches = 0
        files_with_matches = 0
        
        for file_path in files_to_process:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 执行搜索
                flags = 0 if self.case_sensitive_check.isChecked() else re.IGNORECASE
                
                # 初始化变量
                all_matches = []
                
                # 按句子分割文本（使用中英文句号、问号、感叹号作为分隔符）
                sentences = re.split(r'[.!?。？！]+', content)
                # 保存每个句子的起始和结束位置
                sentence_positions = []
                current_pos = 0
                for sentence in sentences:
                    # 查找句子在原始文本中的实际位置（考虑分隔符）
                    # 尝试在当前位置之后查找句子
                    pos = content.find(sentence, current_pos)
                    if pos != -1:
                        # 查找句子后面的分隔符
                        separator_end = pos + len(sentence)
                        while separator_end < len(content) and content[separator_end] in '.!?。？！':
                            separator_end += 1
                        sentence_positions.append((pos, separator_end))
                        current_pos = separator_end
                
                # 对于每个句子，检查是否包含任何关键词
                unique_matches = []
                matched_sentence_indices = set()
                
                for keyword in search_keywords:
                    if self.use_regex_check.isChecked():
                        # 使用正则表达式搜索
                        matches = list(re.finditer(keyword, content, flags))
                    else:
                        # 简单字符串搜索
                        if self.case_sensitive_check.isChecked():
                            matches = [match for match in re.finditer(re.escape(keyword), content)]
                        else:
                            matches = [match for match in re.finditer(re.escape(keyword), content, re.IGNORECASE)]
                    
                    # 对于每个匹配，找出它属于哪个句子
                    for match in matches:
                        match_pos = match.start()
                        # 查找匹配位置所在的句子
                        for i, (sentence_start, sentence_end) in enumerate(sentence_positions):
                            if sentence_start <= match_pos < sentence_end:
                                if i not in matched_sentence_indices:
                                    matched_sentence_indices.add(i)
                                    unique_matches.append(match)
                                break
                
                # 如果没有找到句子位置或者句子数量为0，回退到原始的按位置去重逻辑
                if not unique_matches and all_matches:
                    # 去重，按位置排序
                    seen_positions = set()
                    unique_matches = []
                    for match in all_matches:
                        if isinstance(match, re.Match):
                            pos = match.start()
                            if pos not in seen_positions:
                                seen_positions.add(pos)
                                unique_matches.append(match)
                        else:
                            pos = match
                            if pos not in seen_positions:
                                seen_positions.add(pos)
                                unique_matches.append(match)
                
                if unique_matches:
                    files_with_matches += 1
                    total_matches += len(unique_matches)
                    self.preview_results.append((file_path, content, len(unique_matches)))
                    
                    # 显示文件中找到的匹配数
                    try:
                        # 尝试获取相对路径，如果在不同驱动器则使用文件名
                        rel_path = os.path.relpath(file_path, self.folder_path)
                    except ValueError:
                        # 如果路径在不同驱动器上，直接使用文件名
                        rel_path = os.path.basename(file_path)
                    # 在文件之间添加空行
                    self.log_edit.append("")
                    self.log_edit.append(f"在 【{rel_path}】 中找到 {len(unique_matches)} 处匹配")
                    
                    # 显示完整匹配内容
                    if self.use_regex_check.isChecked():
                        # 对于正则表达式，显示所有匹配
                        for i, match in enumerate([m for m in unique_matches if isinstance(m, re.Match)]):
                            start = max(0, match.start() - 20)
                            end = min(len(content), match.end() + 20)
                            context = content[start:end]
                            # 在命中之间添加空行（除了第一个命中）
                            if i > 0:
                                self.log_edit.append("")
                            self.log_edit.append(f"^^^^^^^^^匹配 {i+1}:")
                            self.log_edit.append(f"{context}")
                    else:
                        # 对于普通文本，显示所有匹配位置的上下文
                        for i, pos in enumerate([m.start() if isinstance(m, re.Match) else m for m in unique_matches]):
                            # 使用第一个关键词估算长度（实际匹配可能来自不同关键词）
                            keyword_len = len(search_keywords[0]) if search_keywords else 0
                            start = max(0, pos - 20)
                            end = min(len(content), pos + keyword_len + 20)
                            context = content[start:end]
                            # 在命中之间添加空行（除了第一个命中）
                            if i > 0:
                                self.log_edit.append("")
                            self.log_edit.append(f"^^^^^^^^^匹配 {i+1}:")
                            self.log_edit.append(f"{context}")
        
            except UnicodeDecodeError:
                try:
                    # 尝试获取相对路径，如果在不同驱动器则使用文件名
                    rel_path = os.path.relpath(file_path, self.folder_path)
                except ValueError:
                    # 如果路径在不同驱动器上，直接使用文件名
                    rel_path = os.path.basename(file_path)
                self.log_edit.append(f"跳过二进制文件: {rel_path}")
            except Exception as e:
                try:
                    # 尝试获取相对路径，如果在不同驱动器则使用文件名
                    rel_path = os.path.relpath(file_path, self.folder_path)
                except ValueError:
                    # 如果路径在不同驱动器上，直接使用文件名
                    rel_path = os.path.basename(file_path)
                self.log_edit.append(f"处理文件 {rel_path} 时出错: {str(e)}")
        
        self.log_edit.append(f"\n搜索完成！")
        self.log_edit.append(f"在 {files_with_matches} 个文件中找到 {total_matches} 处匹配")
        
        if total_matches > 0:
            QMessageBox.information(self, "搜索完成", f"在 {files_with_matches} 个文件中找到 {total_matches} 处匹配\n点击'替换'执行实际替换操作")
        else:
            QMessageBox.information(self, "未找到匹配", "没有找到与搜索条件匹配的内容")
    
    def start_replace(self):
        """开始执行替换操作"""
        # 验证输入
        if not self.folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹！")
            return
        
        search_input = self.search_edit.currentText()
        if not search_input:
            QMessageBox.warning(self, "警告", "请输入查找内容！")
            return
        
        # 解析多关键词
        search_keywords = self.parse_search_keywords(search_input)
        
        # 如果没有预览结果，先执行预览
        if not self.preview_results:
            reply = QMessageBox.question(self, "确认操作", "您还没有搜索结果，是否继续？", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            # 执行搜索以获取文件列表
            self.preview_replace()
            # 如果还是没有结果，直接返回
            if not self.preview_results:
                return
        
        # 再次确认替换操作
        total_matches = sum(count for _, _, count in self.preview_results)
        reply = QMessageBox.question(self, "确认替换", f"确定要替换所有 {total_matches} 处匹配吗？\n此操作无法撤销！", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log_edit.append("\n开始执行替换操作...")
        self.log_edit.append(f"替换关键词: {', '.join(search_keywords)}")
        
        files_changed = 0
        total_replaced = 0
        errors = 0
        
        replace_text = self.replace_edit.text()
        
        for file_path, original_content, _ in self.preview_results:
            try:
                # 执行替换，同时按照句子级别计算匹配数
                flags = 0 if self.case_sensitive_check.isChecked() else re.IGNORECASE
                new_content = original_content
                
                # 按句子分割文本（使用中英文句号、问号、感叹号作为分隔符）
                sentences = re.split(r'[.!?。？！]+', original_content)
                # 保存每个句子的起始和结束位置
                sentence_positions = []
                current_pos = 0
                for sentence in sentences:
                    # 查找句子在原始文本中的实际位置
                    pos = original_content.find(sentence, current_pos)
                    if pos != -1:
                        # 查找句子后面的分隔符
                        separator_end = pos + len(sentence)
                        while separator_end < len(original_content) and original_content[separator_end] in '.!?。？！':
                            separator_end += 1
                        sentence_positions.append((pos, separator_end))
                        current_pos = separator_end
                
                # 统计包含至少一个关键词的句子数量
                matched_sentence_indices = set()
                for keyword in search_keywords:
                    if self.use_regex_check.isChecked():
                        matches = list(re.finditer(keyword, original_content, flags))
                    else:
                        if self.case_sensitive_check.isChecked():
                            matches = [match for match in re.finditer(re.escape(keyword), original_content)]
                        else:
                            matches = [match for match in re.finditer(re.escape(keyword), original_content, re.IGNORECASE)]
                    
                    # 对于每个匹配，找出它属于哪个句子
                    for match in matches:
                        match_pos = match.start()
                        for i, (sentence_start, sentence_end) in enumerate(sentence_positions):
                            if sentence_start <= match_pos < sentence_end:
                                matched_sentence_indices.add(i)
                                break
                
                # 执行实际替换
                total_count = 0
                for keyword in search_keywords:
                    if self.use_regex_check.isChecked():
                        new_content, count = re.subn(keyword, replace_text, new_content, flags=flags)
                    else:
                        if self.case_sensitive_check.isChecked():
                            count = new_content.count(keyword)
                            new_content = new_content.replace(keyword, replace_text)
                        else:
                            # 不区分大小写的字符串替换
                            new_content = re.sub(re.escape(keyword), replace_text, new_content, flags=re.IGNORECASE)
                            count = len(re.findall(re.escape(keyword), original_content, flags=re.IGNORECASE))
                    # 注意：这里的count是实际替换次数，但我们统计的是句子数量
                
                # 使用句子级别的计数作为替换计数
                count = len(matched_sentence_indices)
                
                # 写入新内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                files_changed += 1
                total_replaced += count
                try:
                    # 尝试获取相对路径，如果在不同驱动器则使用文件名
                    rel_path = os.path.relpath(file_path, self.folder_path)
                except ValueError:
                    # 如果路径在不同驱动器上，直接使用文件名
                    rel_path = os.path.basename(file_path)
                self.log_edit.append(f"已替换 {rel_path} 中的 {count} 处匹配")
                
            except Exception as e:
                errors += 1
                try:
                    # 尝试获取相对路径，如果在不同驱动器则使用文件名
                    rel_path = os.path.relpath(file_path, self.folder_path)
                except ValueError:
                    # 如果路径在不同驱动器上，直接使用文件名
                    rel_path = os.path.basename(file_path)
                self.log_edit.append(f"替换 {rel_path} 时出错: {str(e)}")
        
        # 完成消息
        self.log_edit.append(f"\n替换完成！")
        self.log_edit.append(f"成功修改: {files_changed} 个文件")
        self.log_edit.append(f"替换总数: {total_replaced} 处")
        self.log_edit.append(f"失败: {errors} 个文件")
        
        QMessageBox.information(self, "完成", f"替换操作已完成！\n成功修改: {files_changed} 个文件\n替换总数: {total_replaced} 处\n失败: {errors} 个文件")