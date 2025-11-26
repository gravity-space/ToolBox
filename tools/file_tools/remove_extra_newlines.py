import os
import re
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox, QFileDialog, QLineEdit, QHBoxLayout, QTextEdit, QCheckBox, QComboBox
from PyQt6.QtCore import Qt


class RemoveExtraNewlinesDialog(QDialog):
    """删除多余空行工具对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_path = ""  # 初始文件夹路径为空
        # 从config.json中获取窗口标题（使用工具名称）
        if parent and hasattr(parent, 'tools'):
            # 查找当前工具的配置
            for tool in parent.tools:
                if tool.class_name == 'RemoveExtraNewlinesDialog':
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
        self.resize(650, 450)  # 只设置大小，不设置位置
        
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
        
        # 选项设置
        options_layout = QHBoxLayout()
        self.include_subfolders_check = QCheckBox("包含子文件夹")
        self.include_subfolders_check.setChecked(True)
        
        options_layout.addWidget(self.include_subfolders_check)
        options_layout.addStretch()
        main_layout.addLayout(options_layout)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        preview_btn = QPushButton("预览")
        preview_btn.clicked.connect(self.preview_remove)
        process_btn = QPushButton("开始处理")
        process_btn.clicked.connect(self.start_process)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        
        button_layout.addWidget(preview_btn)
        button_layout.addWidget(process_btn)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)
        
        # 日志输出区域
        log_label = QLabel("操作日志:")
        main_layout.addWidget(log_label)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        main_layout.addWidget(self.log_edit)
        
        # 存储预览结果，用于后续处理
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
    
    def remove_extra_newlines(self, content):
        """删除多余空行，保留至多一个空行，并确保文件开头不是空行"""
        # 1. 首先移除文件开头的所有空行和空白字符
        modified_content = re.sub(r'^[\s\n]+', '', content)
        
        # 2. 然后将多个连续的换行符替换为单个换行符
        # 注意：这里需要保留单个空行，所以将两个或多个连续换行符替换为两个换行符
        # 这样就保留了至多一个空行
        modified_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', modified_content)
        
        return modified_content
    
    def preview_remove(self):
        """预览处理结果"""
        # 验证输入
        if not self.folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹！")
            return
        
        self.log_edit.clear()
        self.log_edit.append("开始预览处理结果...")
        self.preview_results = []
        
        files_to_process = self.get_files_to_process()
        self.log_edit.append(f"找到 {len(files_to_process)} 个文件待处理")
        
        files_with_extra_newlines = 0
        
        for file_path in files_to_process:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                # 执行删除多余空行的操作
                modified_content = self.remove_extra_newlines(original_content)
                
                # 检查文件是否有变化
                if modified_content != original_content:
                    files_with_extra_newlines += 1
                    self.preview_results.append((file_path, original_content, modified_content))
                    
                    # 计算空行变化
                    original_empty_lines = original_content.count('\n\n')
                    modified_empty_lines = modified_content.count('\n\n')
                    
                    rel_path = os.path.relpath(file_path, self.folder_path)
                    self.log_edit.append(f"文件 {rel_path} 中存在多余空行")
                    self.log_edit.append(f"  原连续空行数: {original_empty_lines}, 修改后连续空行数: {modified_empty_lines}")
                else:
                    rel_path = os.path.relpath(file_path, self.folder_path)
                    self.log_edit.append(f"文件 {rel_path} 无需修改")
            
            except UnicodeDecodeError:
                self.log_edit.append(f"跳过二进制文件: {os.path.relpath(file_path, self.folder_path)}")
            except Exception as e:
                self.log_edit.append(f"处理文件 {os.path.relpath(file_path, self.folder_path)} 时出错: {str(e)}")
        
        self.log_edit.append(f"\n预览完成！")
        self.log_edit.append(f"需要处理: {files_with_extra_newlines} 个文件")
        
        if files_with_extra_newlines > 0:
            QMessageBox.information(self, "预览完成", f"发现 {files_with_extra_newlines} 个文件中存在多余空行\n点击'开始处理'执行实际操作")
        else:
            QMessageBox.information(self, "无需处理", "所有文件都已经是正确的空行格式，无需处理")
    
    def start_process(self):
        """开始执行删除多余空行的操作"""
        # 验证输入
        if not self.folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹！")
            return
        
        # 如果没有预览结果，先执行预览
        if not self.preview_results:
            reply = QMessageBox.question(self, "确认操作", "您还没有预览处理结果，是否继续？", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            # 执行预览以获取文件列表
            self.preview_remove()
            # 如果还是没有结果，直接返回
            if not self.preview_results:
                return
        
        # 确认处理操作
        reply = QMessageBox.question(self, "确认处理", f"确定要处理 {len(self.preview_results)} 个文件吗？\n此操作将修改文件内容！", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log_edit.append("\n开始执行删除多余空行操作...")
        
        files_processed = 0
        errors = 0
        
        for file_path, _, modified_content in self.preview_results:
            try:
                # 写入新内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                files_processed += 1
                rel_path = os.path.relpath(file_path, self.folder_path)
                self.log_edit.append(f"已处理: {rel_path}")
                
            except Exception as e:
                errors += 1
                rel_path = os.path.relpath(file_path, self.folder_path)
                self.log_edit.append(f"处理 {rel_path} 时出错: {str(e)}")
        
        # 完成消息
        self.log_edit.append(f"\n处理完成！")
        self.log_edit.append(f"成功处理: {files_processed} 个文件")
        self.log_edit.append(f"失败: {errors} 个文件")
        
        QMessageBox.information(self, "完成", f"删除多余空行操作已完成！\n成功处理: {files_processed} 个文件\n失败: {errors} 个文件")
