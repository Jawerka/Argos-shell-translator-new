# PyInstaller hook для argostranslate.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("argostranslate")
datas = collect_data_files("argostranslate")
hiddenimports += [
    "argostranslate.translate",
    "argostranslate.apis",
    "argostranslate.cli",
    "argostranslate.package",
    "argostranslate.tags",
    "argostranslate.apply_bpe",
    "argostranslate.argospm",
    "argostranslate.utils",
    "argostranslate.__main__",
]
