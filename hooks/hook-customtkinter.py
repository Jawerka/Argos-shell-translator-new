# PyInstaller hook для customtkinter (темы, assets).
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("customtkinter")
hiddenimports += ["darkdetect"]
datas = collect_data_files("customtkinter")
