# PyInstaller hook для numpy.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = [
    m
    for m in collect_submodules("numpy")
    if not m.endswith(".tests")
    and "f2py.tests" not in m
    and "distutils.tests" not in m
]
datas = collect_data_files("numpy")
