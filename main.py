import sys
import os
import json
import importlib

# 全局引入数据库模块
from database import db_manager, execute_query, execute_non_query, create_table, table_exists, get_tables
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QPushButton, QGridLayout, QLabel, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class Tool:
    """工具类，用于管理工具的基本信息"""
    def __init__(self, name, description, group, module=None, class_name=None):
        self.name = name
        self.description = description
        self.group = group
        self.module = module  # Python模块路径
        self.class_name = class_name  # 工具类名称


class ToolBoxApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # 初始化工具列表
        self.tools = self.initialize_tools()
        self.init_ui()
        
        # 存储工具对话框引用，防止被垃圾回收
        self.active_tool_dialogs = []
        
        # 连接窗口大小变化事件，当窗口调整大小时重新计算布局
        self.resizeEvent = self.on_resize

    def load_config(self):
        """加载配置文件"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "配置错误", f"加载配置文件失败: {str(e)}")
            return {"tools": []}
    
    def initialize_tools(self):
        """从配置文件初始化所有工具"""
        config = self.load_config()
        tools = []
        
        for tool_config in config.get("tools", []):
            # 为Tool对象添加额外的配置信息
            tool = Tool(
                name=tool_config.get("name", ""),
                description=tool_config.get("description", ""),
                group=tool_config.get("group", ""),
                module=tool_config.get("module", None),
                class_name=tool_config.get("class", None)
            )
            tools.append(tool)
        
        return tools
    
    def init_ui(self):
        # 设置窗口基本属性
        self.setWindowTitle('工具箱')
        self.setGeometry(100, 100, 800, 600)
        
        # 设置应用字体
        font = QFont()
        font.setFamily("SimHei")
        font.setPointSize(10)
        self.setFont(font)
        
        # 创建中心部件和标签页控件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建标签页用于分组展示工具
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)  # 不允许关闭标签页
        self.tabs.setStyleSheet("QTabBar::tab { height: 30px; width: 120px; }")
        
        # 创建各个工具分组
        self.create_tool_tabs()
        
        # 添加标签页到主布局
        self.main_layout.addWidget(self.tabs)
    
    def create_tool_tabs(self):
        """根据工具分组创建标签页"""
        # 保留配置文件中的分组顺序
        groups = []
        seen_groups = set()
        for tool in self.tools:
            if tool.group not in seen_groups:
                groups.append(tool.group)
                seen_groups.add(tool.group)
        
        # 为每个分组创建标签页
        for group in groups:
            # 创建标签页和布局
            tab_widget = QWidget()
            grid_layout = QGridLayout(tab_widget)
            grid_layout.setSpacing(20)
            grid_layout.setContentsMargins(20, 20, 20, 20)
            # 设置布局垂直对齐方式为顶部对齐
            grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            
            # 获取当前分组的所有工具
            group_tools = [tool for tool in self.tools if tool.group == group]
            
            # 使用固定的按钮宽度，确保一致性
            button_width = 150
            
            # 获取标签页内容区域的实际可用宽度
            # 主窗口宽度减去标签页边框、边距和滚动条可能占用的空间
            available_width = self.width() - 50  # 调整边距估算值，使其更紧凑
            
            # 计算按钮和间距的总宽度
            spacing = grid_layout.spacing()
            item_width = button_width + spacing  # 每个按钮项占用的总宽度（包含右侧间距）
            
            # 动态计算每行最多可以显示的工具数量
            # 确保至少显示1个工具，最多不超过10个（避免过多导致按钮过小）
            max_columns = min(10, max(1, available_width // item_width))
            
            # 额外检查：如果计算出的列数导致按钮总宽度远小于可用宽度，则增加一列
            total_width = max_columns * item_width - spacing  # 最后一个按钮不需要右侧间距
            if total_width < available_width * 0.8 and max_columns < 10:
                max_columns += 1
            
            # 创建工具按钮并添加到布局
            for index, tool in enumerate(group_tools):
                btn = self.create_tool_button(tool)
                
                # 计算行列位置
                row = index // max_columns
                col = index % max_columns
                
                # 设置按钮的固定宽度，确保无论工具数量多少，按钮宽度一致
                btn.setFixedWidth(150)
                
                grid_layout.addWidget(btn, row, col)
            
            # 设置列拉伸因子，让按钮在水平方向均匀分布
            # 移除之前可能设置的拉伸因子，避免影响新的布局
            for i in range(max_columns):
                try:
                    grid_layout.setColumnStretch(i, 0)
                except:
                    pass  # 忽略可能的索引错误
            
            # 只在最后一列设置拉伸因子，使按钮组整体居中且不会浪费太多空间
            if max_columns > 0:
                grid_layout.setColumnStretch(max_columns, 1)
            
            # 添加行拉伸因子，确保内容在垂直方向顶部对齐
            grid_layout.setRowStretch(grid_layout.rowCount(), 1)
            
            # 添加标签页
            self.tabs.addTab(tab_widget, group)
            
    def on_resize(self, event):
        """窗口大小变化时重新计算布局"""
        # 重新创建标签页，以更新工具按钮的布局
        # 先保存当前选中的标签页索引
        current_index = self.tabs.currentIndex()
        
        # 清除所有标签页
        self.tabs.clear()
        
        # 重新创建标签页
        self.create_tool_tabs()
        
        # 恢复之前选中的标签页
        if current_index >= 0 and current_index < self.tabs.count():
            self.tabs.setCurrentIndex(current_index)
        
        # 调用父类的resizeEvent方法
        super().resizeEvent(event)
    
    def create_tool_button(self, tool):
        """创建工具按钮"""
        btn = QPushButton(tool.name)
        btn.setMinimumSize(150, 90)
        btn.setToolTip(tool.description)
        
        # 设置按钮样式
        btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 8px;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #999;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        # 连接按钮点击事件
        btn.clicked.connect(lambda checked, t=tool: self.on_tool_clicked(t))
        
        return btn
    
    def on_tool_clicked(self, tool):
        """处理工具按钮点击事件"""
        self.statusBar().showMessage(f'正在启动: {tool.name}')
        
        try:
            # 尝试动态导入工具类
            if tool.module and tool.class_name:
                # 动态导入模块
                module = importlib.import_module(tool.module)
                # 获取类
                tool_class = getattr(module, tool.class_name)
                # 创建实例
                dialog = tool_class(self)
                
                # 检查对话框是否已被拒绝（密码验证失败或用户取消）
                # 通过检查对话框的windowTitle是否被设置来判断初始化是否成功
                if dialog.windowTitle():
                    # 使用show()而非exec()来创建非模态窗口
                    dialog.show()
                    # 保存引用到列表中，防止被垃圾回收
                    self.active_tool_dialogs.append(dialog)
                    # 当对话框关闭时，从列表中移除
                    dialog.destroyed.connect(lambda d=dialog: self.active_tool_dialogs.remove(d) if d in self.active_tool_dialogs else None)
            else:
                # 其他工具暂时显示提示
                QMessageBox.information(self, "提示", f"{tool.name} - {tool.description}\n\n该功能正在开发中...")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动工具 '{tool.name}' 失败: {str(e)}")
        
        self.statusBar().showMessage('就绪')


def main():
    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 创建主窗口实例
    window = ToolBoxApp()
    
    # 显示窗口并最大化
    window.show()
    window.showMaximized()
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == '__main__':
    main()