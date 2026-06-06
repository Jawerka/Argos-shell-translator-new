# Assets

Статические ресурсы приложения:

- `argos_translate.ico` — иконка окна и трея
- `argos_translate.png` — запасной формат для pystray

При сборке EXE файлы копируются в `assets/` внутри дистрибутива.
Код ищет ресурсы через `get_resource_path("argos_translate.ico")` (сначала `assets/`, затем корень проекта).
