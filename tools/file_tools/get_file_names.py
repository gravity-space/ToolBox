import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox, QFileDialog, QLineEdit, QHBoxLayout, QTextEdit, QCheckBox


class GetFileNamesDialog(QDialog):
    """获取文件名列表工具对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_path = ""
        self.file_names = []
        self.file_names_without_ext = []  # 存储不含后缀的文件名
        # 从config.json中获取窗口标题（使用工具名称）
        if parent and hasattr(parent, 'tools'):
            # 查找当前工具的配置
            for tool in parent.tools:
                if tool.class_name == 'GetFileNamesDialog':
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
        self.resize(600, 400)  # 只设置大小，不设置位置
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 文件夹选择部分
        folder_layout = QHBoxLayout()
        folder_label = QLabel("选择路径:")
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setReadOnly(True)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.select_folder)
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_path_edit)
        folder_layout.addWidget(browse_btn)
        main_layout.addLayout(folder_layout)
        
        # 选项设置
        options_layout = QHBoxLayout()
        options_label = QLabel("选项:")
        self.remove_ext_checkbox = QCheckBox("去掉文件后缀")
        options_layout.addWidget(options_label)
        options_layout.addWidget(self.remove_ext_checkbox)
        options_layout.addStretch()
        main_layout.addLayout(options_layout)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        get_names_btn = QPushButton("获取文件名")
        get_names_btn.clicked.connect(self.get_file_names)
        export_btn = QPushButton("导出为TXT")
        export_btn.clicked.connect(self.export_to_txt)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        
        button_layout.addWidget(get_names_btn)
        button_layout.addWidget(export_btn)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)
        
        # 日志输出区域
        log_label = QLabel("文件名列表:")
        main_layout.addWidget(log_label)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        main_layout.addWidget(self.log_edit)
        
        # 将窗口设置在屏幕中央
        self.center_window()
    
    def select_folder(self):
        """选择文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹", "")
        if folder_path:
            self.folder_path = folder_path
            self.folder_path_edit.setText(folder_path)
            self.log_edit.append(f"已选择文件夹: {folder_path}")
    
    def get_file_names(self):
        """获取文件夹下的所有文件名"""
        # 验证输入
        if not self.folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹！")
            return
        
        try:
            # 清空之前的列表
            self.file_names = []
            self.file_names_without_ext = []
            self.log_edit.clear()
            
            # 获取选项状态
            remove_ext = self.remove_ext_checkbox.isChecked()
            
            self.log_edit.append(f"正在获取 {self.folder_path} 下的所有文件名...")
            if remove_ext:
                self.log_edit.append("选项: 去掉文件后缀")
            
            # 遍历文件夹中的所有文件
            file_count = 0
            
            for filename in os.listdir(self.folder_path):
                file_path = os.path.join(self.folder_path, filename)
                
                # 只处理文件，跳过文件夹
                if os.path.isfile(file_path):
                    self.file_names.append(filename)
                    
                    # 根据选项决定显示和存储的文件名
                    if remove_ext:
                        name_without_ext, _ = os.path.splitext(filename)
                        self.file_names_without_ext.append(name_without_ext)
                        self.log_edit.append(name_without_ext)
                    else:
                        self.file_names_without_ext.append(filename)
                        self.log_edit.append(filename)
                    
                    file_count += 1
            
            # 完成消息
            self.log_edit.append(f"\n获取完成！共找到 {file_count} 个文件")
            
        except Exception as e:
            self.log_edit.append(f"操作失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"操作失败: {str(e)}")
    
    def export_to_txt(self):
        """将文件名列表导出为TXT文件"""
        if not self.file_names:
            QMessageBox.warning(self, "警告", "请先获取文件名列表！")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "导出为TXT", 
            os.path.join(os.path.expanduser("~"), "文件名列表.txt"),
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                # 获取选项状态
                remove_ext = self.remove_ext_checkbox.isChecked()
                
                # 写入文件，根据之前获取时的选项状态决定使用哪个列表
                with open(file_path, 'w', encoding='utf-8') as f:
                    for filename in self.file_names_without_ext:
                        f.write(f"{filename}\n")
                
                self.log_edit.append(f"\n已成功导出到: {file_path}")
                QMessageBox.information(self, "成功", f"文件名列表已成功导出到:\n{file_path}")
                
            except Exception as e:
                self.log_edit.append(f"导出失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")