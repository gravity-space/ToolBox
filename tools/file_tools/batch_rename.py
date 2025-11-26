import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox, QFileDialog, QLineEdit, QHBoxLayout, QTextEdit


class BatchRenameDialog(QDialog):
    """批量重命名工具对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_path = ""  # 初始文件夹路径为空
        # 从config.json中获取窗口标题（使用工具名称）
        if parent and hasattr(parent, 'tools'):
            # 查找当前工具的配置
            for tool in parent.tools:
                if tool.class_name == 'BatchRenameDialog':
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
        
        # 操作按钮
        button_layout = QHBoxLayout()
        rename_btn = QPushButton("开始重命名")
        rename_btn.clicked.connect(self.start_rename)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        
        button_layout.addWidget(rename_btn)
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
    
    def select_folder(self):
        """选择文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹", "")
        if folder_path:
            self.folder_path = folder_path
            self.folder_path_edit.setText(folder_path)
            self.log_edit.append(f"已选择文件夹: {folder_path}")
    
    def start_rename(self):
        """开始批量重命名"""
        # 验证输入
        if not self.folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹！")
            return
        
        self.log_edit.append(f"开始批量重命名，按默认格式处理...")
        
        try:
            # 遍历文件夹中的所有文件
            files_renamed = 0
            errors = 0
            
            for filename in os.listdir(self.folder_path):
                file_path = os.path.join(self.folder_path, filename)
                
                # 跳过文件夹
                if os.path.isdir(file_path):
                    continue
                
                try:
                    # 获取文件名和扩展名
                    name, ext = os.path.splitext(filename)
                    
                    # 应用重命名规则
                    new_name = self.apply_rename_rule(name, None)
                    
                    if new_name != name:
                        # 构建新的完整文件名
                        new_filename = new_name + ext
                        new_file_path = os.path.join(self.folder_path, new_filename)
                        
                        # 检查是否有同名文件
                        counter = 1
                        while os.path.exists(new_file_path):
                            new_filename = f"{new_name}_{counter}{ext}"
                            new_file_path = os.path.join(self.folder_path, new_filename)
                            counter += 1
                        
                        # 执行重命名
                        os.rename(file_path, new_file_path)
                        self.log_edit.append(f"重命名: {filename} -> {new_filename}")
                        files_renamed += 1
                    else:
                        self.log_edit.append(f"跳过: {filename} (无需更改)")
                
                except Exception as e:
                    self.log_edit.append(f"错误: {filename} - {str(e)}")
                    errors += 1
            
            # 完成消息
            self.log_edit.append(f"\n重命名完成！")
            self.log_edit.append(f"成功: {files_renamed} 个文件")
            self.log_edit.append(f"失败: {errors} 个文件")
            
            QMessageBox.information(self, "完成", f"批量重命名已完成！\n成功: {files_renamed} 个文件\n失败: {errors} 个文件")
            
        except Exception as e:
            self.log_edit.append(f"操作失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"操作失败: {str(e)}")
    
    def apply_rename_rule(self, filename, _template):
        """应用重命名规则"""
        # 按照《测试》格式处理文件名
        
        # 检查文件名是否已经包含书名号
        if '《' in filename and '》' in filename:
            # 提取书名号之间的内容
            start_idx = filename.find('《')
            end_idx = filename.find('》')
            if start_idx < end_idx:
                # 提取书名号及其中的内容
                book_title = filename[start_idx:end_idx+1]
                return book_title
        
        # 简化处理：直接给整个文件名加上书名号
        return f"《{filename}》"