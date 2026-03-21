```ps1
pyinstaller --onefile --windowed --icon=icon_light.ico --name "ArgosTranslator" `
  --hidden-import=pystray._win32 `
  --hidden-import=pystray._darwin `
  --hidden-import=pystray._xorg `
  --hidden-import=argostranslate.package `
  --hidden-import=argostranslate.translate `
  --exclude-module=torch `
  --exclude-module=tensorboard `
  --exclude-module=sympy `
  --clean `
  main.py
```