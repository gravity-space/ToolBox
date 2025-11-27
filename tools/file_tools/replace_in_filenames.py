import os
import re
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox, QFileDialog, QLineEdit, QHBoxLayout, QTextEdit, QCheckBox, QComboBox
from PyQt6.QtCore import Qt


class ReplaceInFilenamesDialog(QDialog):
    """替换文件名中字符工具对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_path = ""  # 初始文件夹路径为空
        self.preview_results = []  # 存储预览结果 (原文件路径, 新文件名)
        # 从config.json中获取窗口标题（使用工具名称）
        if parent and hasattr(parent, 'tools'):
            # 查找当前工具的配置
            for tool in parent.tools:
                if tool.class_name == 'ReplaceInFilenamesDialog':
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
        
        # 查找替换部分
        find_replace_layout = QVBoxLayout()
        
        # 查找内容
        find_layout = QHBoxLayout()
        find_label = QLabel("查找:")
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("输入要查找的字符或字符串")
        find_layout.addWidget(find_label)
        find_layout.addWidget(self.find_edit)
        
        # 替换内容
        replace_layout = QHBoxLayout()
        replace_label = QLabel("替换为:")
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("输入要替换成的字符或字符串")
        replace_layout.addWidget(replace_label)
        replace_layout.addWidget(self.replace_edit)
        
        find_replace_layout.addLayout(find_layout)
        find_replace_layout.addLayout(replace_layout)
        main_layout.addLayout(find_replace_layout)
        
        # 选项设置
        options_layout = QVBoxLayout()
        
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
        
        # 其他选项
        other_options_layout = QHBoxLayout()
        self.include_subfolders_check = QCheckBox("包含子文件夹")
        self.include_subfolders_check.setChecked(True)
        self.match_case_check = QCheckBox("区分大小写")
        self.match_case_check.setChecked(True)
        
        other_options_layout.addWidget(self.include_subfolders_check)
        other_options_layout.addWidget(self.match_case_check)
        other_options_layout.addStretch()
        
        options_layout.addLayout(file_type_layout)
        options_layout.addLayout(other_options_layout)
        main_layout.addLayout(options_layout)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        preview_btn = QPushButton("预览")
        preview_btn.clicked.connect(self.preview_replace)
        replace_btn = QPushButton("开始替换")
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
    
    def get_new_filename(self, filename, find_text, replace_text, match_case=True):
        """获取替换后的新文件名"""
        if not find_text:
            return filename
        
        if match_case:
            return filename.replace(find_text, replace_text)
        else:
            # 不区分大小写的替换
            flags = re.IGNORECASE
            return re.sub(re.escape(find_text), replace_text, filename, flags=flags)
    
    def preview_replace(self):
        """预览替换结果"""
        # 验证输入
        if not self.folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹！")
            return
        
        find_text = self.find_edit.text()
        if not find_text:
            QMessageBox.warning(self, "警告", "请输入要查找的字符！")
            return
        
        self.log_edit.clear()
        self.log_edit.append("开始预览替换结果...")
        self.preview_results = []
        
        files_to_process = self.get_files_to_process()
        self.log_edit.append(f"找到 {len(files_to_process)} 个文件待检查")
        
        files_to_replace = 0
        replace_text = self.replace_edit.text()
        match_case = self.match_case_check.isChecked()
        
        for file_path in files_to_process:
            try:
                # 获取文件名
                dir_path, filename = os.path.split(file_path)
                
                # 获取新文件名
                new_filename = self.get_new_filename(filename, find_text, replace_text, match_case)
                
                # 检查文件名是否有变化
                if new_filename != filename:
                    # 检查新文件名是否已存在
                    new_file_path = os.path.join(dir_path, new_filename)
                    if os.path.exists(new_file_path):
                        try:
                            # 尝试获取相对路径，如果在不同驱动器则使用文件名
                            rel_path = os.path.relpath(file_path, self.folder_path)
                        except ValueError:
                            # 如果路径在不同驱动器上，直接使用文件名
                            rel_path = os.path.basename(file_path)
                        self.log_edit.append(f"警告: {rel_path} -> {new_filename} (目标文件已存在，将被跳过)")
                    else:
                        files_to_replace += 1
                        self.preview_results.append((file_path, new_filename))
                        try:
                            # 尝试获取相对路径，如果在不同驱动器则使用文件名
                            rel_path = os.path.relpath(file_path, self.folder_path)
                        except ValueError:
                            # 如果路径在不同驱动器上，直接使用文件名
                            rel_path = os.path.basename(file_path)
                        self.log_edit.append(f"将替换: {rel_path} -> {new_filename}")
                else:
                    # 文件名中不存在要查找的字符
                    try:
                        # 尝试获取相对路径，如果在不同驱动器则使用文件名
                        rel_path = os.path.relpath(file_path, self.folder_path)
                    except ValueError:
                        # 如果路径在不同驱动器上，直接使用文件名
                        rel_path = os.path.basename(file_path)
                    self.log_edit.append(f"无需替换: {rel_path}")
            
            except Exception as e:
                try:
                    # 尝试获取相对路径，如果在不同驱动器则使用文件名
                    rel_path = os.path.relpath(file_path, self.folder_path)
                except ValueError:
                    # 如果路径在不同驱动器上，直接使用文件名
                    rel_path = os.path.basename(file_path)
                self.log_edit.append(f"检查文件 {rel_path} 时出错: {str(e)}")
        
        self.log_edit.append(f"\n预览完成！")
        self.log_edit.append(f"将替换: {files_to_replace} 个文件的文件名")
        
        if files_to_replace > 0:
            QMessageBox.information(self, "预览完成", f"将替换 {files_to_replace} 个文件的文件名\n点击'开始替换'执行实际操作")
        else:
            QMessageBox.information(self, "无需替换", "没有找到需要替换的文件名")
    
    def start_replace(self):
        """开始执行替换操作"""
        # 验证输入
        if not self.folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹！")
            return
        
        find_text = self.find_edit.text()
        if not find_text:
            QMessageBox.warning(self, "警告", "请输入要查找的字符！")
            return
        
        # 如果没有预览结果，先执行预览
        if not self.preview_results:
            reply = QMessageBox.question(self, "确认操作", "您还没有预览替换结果，是否继续？", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            # 执行预览以获取文件列表
            self.preview_replace()
            # 如果还是没有结果，直接返回
            if not self.preview_results:
                return
        
        # 确认替换操作
        reply = QMessageBox.question(self, "确认替换", f"确定要替换 {len(self.preview_results)} 个文件的文件名吗？\n此操作将修改文件名！", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log_edit.append("\n开始执行文件名替换操作...")
        
        files_replaced = 0
        errors = 0
        
        for file_path, new_filename in self.preview_results:
            try:
                # 获取目录路径
                dir_path = os.path.dirname(file_path)
                new_file_path = os.path.join(dir_path, new_filename)
                
                # 再次检查文件是否存在，避免并发问题
                if not os.path.exists(new_file_path):
                    # 执行重命名
                    os.rename(file_path, new_file_path)
                    files_replaced += 1
                    try:
                        # 尝试获取相对路径，如果在不同驱动器则使用文件名
                        rel_path = os.path.relpath(file_path, self.folder_path)
                    except ValueError:
                        # 如果路径在不同驱动器上，直接使用文件名
                        rel_path = os.path.basename(file_path)
                    self.log_edit.append(f"已替换: {rel_path} -> {new_filename}")
                else:
                    try:
                        # 尝试获取相对路径，如果在不同驱动器则使用文件名
                        rel_path = os.path.relpath(file_path, self.folder_path)
                    except ValueError:
                        # 如果路径在不同驱动器上，直接使用文件名
                        rel_path = os.path.basename(file_path)
                    self.log_edit.append(f"跳过: {rel_path} (目标文件已存在)")
                    errors += 1
                    
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
        self.log_edit.append(f"成功替换: {files_replaced} 个文件")
        self.log_edit.append(f"失败: {errors} 个文件")
        
        QMessageBox.information(self, "完成", f"文件名替换操作已完成！\n成功替换: {files_replaced} 个文件\n失败: {errors} 个文件")