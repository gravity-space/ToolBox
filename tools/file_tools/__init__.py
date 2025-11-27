"""文件处理工具模块"""
from .batch_rename import BatchRenameDialog
from .search_replace import SearchReplaceDialog
from .remove_extra_newlines import RemoveExtraNewlinesDialog
from .get_file_names import GetFileNamesDialog
from .replace_in_filenames import ReplaceInFilenamesDialog
from .insert_text import InsertTextDialog

__all__ = ['BatchRenameDialog', 'SearchReplaceDialog', 'RemoveExtraNewlinesDialog', 'GetFileNamesDialog', 'ReplaceInFilenamesDialog', 'InsertTextDialog']
