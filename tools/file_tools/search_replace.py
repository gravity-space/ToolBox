import os
import re
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox, QFileDialog, QLineEdit, QHBoxLayout, QTextEdit, QCheckBox, QComboBox
from PyQt6.QtCore import Qt


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
        self.init_ui()
    
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
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.select_folder)
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_path_edit)
        folder_layout.addWidget(browse_btn)
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
        self.search_edit = QLineEdit()
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
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
    
    def preview_replace(self):
        """搜索替换结果"""
        # 验证输入
        if not self.folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹！")
            return

        search_text = self.search_edit.text()
        if not search_text:
            QMessageBox.warning(self, "警告", "请输入查找内容！")
            return

        self.log_edit.clear()
        self.log_edit.append("开始搜索替换结果...")
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
                
                if self.use_regex_check.isChecked():
                    # 使用正则表达式搜索
                    matches = list(re.finditer(search_text, content, flags))
                else:
                    # 简单字符串搜索
                    if self.case_sensitive_check.isChecked():
                        matches = [match.start() for match in re.finditer(re.escape(search_text), content)]
                    else:
                        matches = [match.start() for match in re.finditer(re.escape(search_text), content, re.IGNORECASE)]
                
                if matches:
                    files_with_matches += 1
                    total_matches += len(matches)
                    self.preview_results.append((file_path, content, len(matches)))
                    
                    # 显示文件中找到的匹配数
                    rel_path = os.path.relpath(file_path, self.folder_path)
                    self.log_edit.append(f"在 {rel_path} 中找到 {len(matches)} 处匹配")
                    
                    # 显示部分匹配内容作为预览
                    if self.use_regex_check.isChecked():
                        # 对于正则表达式，显示前几个匹配
                        for i, match in enumerate(matches[:3]):
                            start = max(0, match.start() - 20)
                            end = min(len(content), match.end() + 20)
                            context = content[start:end]
                            self.log_edit.append(f"  匹配 {i+1}:")
                            self.log_edit.append("---------------")
                            self.log_edit.append(f"{context}")
                            self.log_edit.append("---------------")
                    else:
                        # 对于普通文本，显示前几个匹配位置的上下文
                        for i, pos in enumerate(matches[:3]):
                            start = max(0, pos - 20)
                            end = min(len(content), pos + len(search_text) + 20)
                            context = content[start:end]
                            self.log_edit.append(f"  匹配 {i+1}:")
                            self.log_edit.append("---------------")
                            self.log_edit.append(f"{context}")
                            self.log_edit.append("---------------")
        
            except UnicodeDecodeError:
                self.log_edit.append(f"跳过二进制文件: {os.path.relpath(file_path, self.folder_path)}")
            except Exception as e:
                self.log_edit.append(f"处理文件 {os.path.relpath(file_path, self.folder_path)} 时出错: {str(e)}")
        
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
        
        search_text = self.search_edit.text()
        if not search_text:
            QMessageBox.warning(self, "警告", "请输入查找内容！")
            return
        
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
        
        files_changed = 0
        total_replaced = 0
        errors = 0
        
        search_text = self.search_edit.text()
        replace_text = self.replace_edit.text()
        
        for file_path, original_content, _ in self.preview_results:
            try:
                # 执行替换
                flags = 0 if self.case_sensitive_check.isChecked() else re.IGNORECASE
                
                if self.use_regex_check.isChecked():
                    # 使用正则表达式替换
                    new_content, count = re.subn(search_text, replace_text, original_content, flags=flags)
                else:
                    # 简单字符串替换
                    if self.case_sensitive_check.isChecked():
                        new_content = original_content.replace(search_text, replace_text)
                        count = original_content.count(search_text)
                    else:
                        # 不区分大小写的字符串替换
                        new_content = re.sub(re.escape(search_text), replace_text, original_content, flags=re.IGNORECASE)
                        count = len(re.findall(re.escape(search_text), original_content, flags=re.IGNORECASE))
                
                # 写入新内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                files_changed += 1
                total_replaced += count
                rel_path = os.path.relpath(file_path, self.folder_path)
                self.log_edit.append(f"已替换 {rel_path} 中的 {count} 处匹配")
                
            except Exception as e:
                errors += 1
                rel_path = os.path.relpath(file_path, self.folder_path)
                self.log_edit.append(f"替换 {rel_path} 时出错: {str(e)}")
        
        # 完成消息
        self.log_edit.append(f"\n替换完成！")
        self.log_edit.append(f"成功修改: {files_changed} 个文件")
        self.log_edit.append(f"替换总数: {total_replaced} 处")
        self.log_edit.append(f"失败: {errors} 个文件")
        
        QMessageBox.information(self, "完成", f"替换操作已完成！\n成功修改: {files_changed} 个文件\n替换总数: {total_replaced} 处\n失败: {errors} 个文件")