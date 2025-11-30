import os
import re
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox, QFileDialog, QLineEdit, QHBoxLayout, QTextEdit, QCheckBox, QComboBox
from PyQt6.QtCore import Qt


class InsertTextDialog(QDialog):
    """在文件夹内的文件中的特定行插入一行指定文本工具对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_path = ""  # 初始文件夹路径为空
        # 从config.json中获取窗口标题（使用工具名称）
        if parent and hasattr(parent, 'tools'):
            # 查找当前工具的配置
            for tool in parent.tools:
                if hasattr(tool, 'class_name') and tool.class_name == 'InsertTextDialog':
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
            self.setWindowTitle("文本插入")
        self.resize(600, 400)  # 只设置大小，不设置位置
        
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

        # 插入位置输入
        position_layout = QHBoxLayout()
        position_label = QLabel("插入位置 (0为开头, -1为结尾):")
        self.position_edit = QLineEdit("0")  # 默认在开头插入
        
        position_layout.addWidget(position_label)
        position_layout.addWidget(self.position_edit)
        main_layout.addLayout(position_layout)

        # 插入文本输入
        text_label = QLabel("插入文本 (支持多行):")
        main_layout.addWidget(text_label)
        self.text_edit = QTextEdit()
        self.text_edit.setMinimumHeight(100)
        self.text_edit.setPlaceholderText("在此输入要插入的文本，支持多行输入...")
        main_layout.addWidget(self.text_edit)
        
        # 选项设置
        options_layout = QHBoxLayout()
        self.include_subfolders_check = QCheckBox("包含子文件夹")
        self.include_subfolders_check.setChecked(True)
        
        options_layout.addWidget(self.include_subfolders_check)
        main_layout.addLayout(options_layout)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        preview_btn = QPushButton("预览")
        preview_btn.clicked.connect(self.preview_insert)
        insert_btn = QPushButton("插入")
        insert_btn.clicked.connect(self.start_insert)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        
        button_layout.addWidget(preview_btn)
        button_layout.addWidget(insert_btn)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)
        
        # 日志输出区域
        log_label = QLabel("操作日志:")
        main_layout.addWidget(log_label)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        main_layout.addWidget(self.log_edit)
        
        # 存储预览结果，用于后续插入
        self.preview_files = []
        
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
    
    def parse_position(self, position_str):
        """解析插入位置"""
        try:
            position = int(position_str)
            return position
        except ValueError:
            QMessageBox.warning(self, "警告", "插入位置必须是整数！")
            return None
    
    def preview_insert(self):
        """预览插入操作"""
        # 验证输入
        if not self.folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹！")
            return

        insert_text = self.text_edit.toPlainText()
        if not insert_text.strip():
            QMessageBox.warning(self, "警告", "请输入要插入的文本！")
            return
        
        position = self.parse_position(self.position_edit.text())
        if position is None:
            return
        
        self.log_edit.clear()
        self.log_edit.append("开始预览插入操作...")
        self.preview_files = []
        
        files_to_process = self.get_files_to_process()
        self.log_edit.append(f"找到 {len(files_to_process)} 个文件待处理")
        
        valid_files = 0
        
        for file_path in files_to_process:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # 计算实际插入位置
                if position == -1:
                    actual_position = len(lines)
                elif position < 0:
                    actual_position = max(0, len(lines) + position)
                else:
                    actual_position = min(position, len(lines))
                
                valid_files += 1
                self.preview_files.append((file_path, lines, actual_position))
                
                # 显示预览信息
                rel_path = os.path.relpath(file_path, self.folder_path)
                self.log_edit.append(f"将在 {rel_path} 的第 {actual_position} 行前插入文本（插入位置在插入内容前面）")
                
                # 显示部分文件内容作为预览
                start_line = max(0, actual_position - 2)
                end_line = min(len(lines), actual_position + 3)
                
                # 对于多行文本，在预览中显示第一行和行数信息
                insert_lines = insert_text.split('\n')
                preview_text = insert_lines[0]
                if len(insert_lines) > 1:
                    preview_text += f"... (共{len(insert_lines)}行)"
                
                for i in range(start_line, end_line):
                    if i == actual_position:
                        self.log_edit.append(f"  > 【将在此处插入】 {preview_text}")
                    else:
                        self.log_edit.append(f"  {i}: {lines[i].rstrip()}")
                if end_line == len(lines) and actual_position == len(lines):
                    self.log_edit.append(f"  > 【将在此处插入】 {preview_text}")
                
                self.log_edit.append("---------------")
            
            except UnicodeDecodeError:
                self.log_edit.append(f"跳过二进制文件: {os.path.relpath(file_path, self.folder_path)}")
            except Exception as e:
                self.log_edit.append(f"读取文件 {os.path.relpath(file_path, self.folder_path)} 时出错: {str(e)}")
        
        self.log_edit.append(f"\n预览完成！")
        self.log_edit.append(f"将对 {valid_files} 个文件执行插入操作")
        
        if valid_files > 0:
            QMessageBox.information(self, "预览完成", f"将对 {valid_files} 个文件执行插入操作\n点击'插入'执行实际插入操作")
        else:
            QMessageBox.information(self, "无文件可处理", "没有找到符合条件的有效文件")
    
    def start_insert(self):
        """开始执行插入操作"""
        # 验证输入
        if not self.folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹！")
            return
        
        insert_text = self.text_edit.toPlainText()
        if not insert_text.strip():
            QMessageBox.warning(self, "警告", "请输入要插入的文本！")
            return
        
        position = self.parse_position(self.position_edit.text())
        if position is None:
            return
        
        # 如果没有预览结果，先执行预览
        if not self.preview_files:
            reply = QMessageBox.question(self, "确认操作", "您还没有预览结果，是否继续？", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            # 执行预览以获取文件列表
            self.preview_insert()
            # 如果还是没有结果，直接返回
            if not self.preview_files:
                return
        
        # 再次确认插入操作
        reply = QMessageBox.question(self, "确认插入", f"确定要对 {len(self.preview_files)} 个文件执行插入操作吗？\n此操作无法撤销！", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log_edit.append("\n开始执行插入操作...")
        
        files_changed = 0
        errors = 0
        
        # 确保文本以换行符结尾
        if not insert_text.endswith('\n'):
            insert_text += '\n'
        
        for file_path, lines, actual_position in self.preview_files:
            try:
                # 执行插入
                new_lines = lines.copy()
                new_lines.insert(actual_position, insert_text)
                
                # 写入新内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                
                files_changed += 1
                try:
                    # 尝试获取相对路径，如果在不同驱动器则使用文件名
                    rel_path = os.path.relpath(file_path, self.folder_path)
                except ValueError:
                    # 如果路径在不同驱动器上，直接使用文件名
                    rel_path = os.path.basename(file_path)
                self.log_edit.append(f"已在 {rel_path} 的第 {actual_position} 行前插入文本（插入位置在插入内容前面）")
                
            except Exception as e:
                errors += 1
                try:
                    # 尝试获取相对路径，如果在不同驱动器则使用文件名
                    rel_path = os.path.relpath(file_path, self.folder_path)
                except ValueError:
                    # 如果路径在不同驱动器上，直接使用文件名
                    rel_path = os.path.basename(file_path)
                self.log_edit.append(f"插入 {rel_path} 时出错: {str(e)}")
        
        # 完成消息
        self.log_edit.append(f"\n插入完成！")
        self.log_edit.append(f"成功修改: {files_changed} 个文件")
        self.log_edit.append(f"失败: {errors} 个文件")
        
        QMessageBox.information(self, "完成", f"插入操作已完成！\n成功修改: {files_changed} 个文件\n失败: {errors} 个文件")