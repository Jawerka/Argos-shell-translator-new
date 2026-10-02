// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Russian (`ru`).
class AppLocalizationsRu extends AppLocalizations {
  AppLocalizationsRu([String locale = 'ru']) : super(locale);

  @override
  String get appTitle => 'Argos Translate';

  @override
  String get trayShow => 'Показать';

  @override
  String get trayExit => 'Выход';

  @override
  String get bootFailedTitle => 'Не удалось запустить';

  @override
  String get openLog => 'Открыть лог';

  @override
  String get statusReady => 'Готово';

  @override
  String get sourcePanelTitle => 'Исходный текст';

  @override
  String get translationPanelTitle => 'Перевод';

  @override
  String get emptyTranslationHint => 'Введите текст слева';

  @override
  String get loading => 'Загрузка…';

  @override
  String get fileMenu => 'Файл';

  @override
  String get fileOpen => 'Открыть…';

  @override
  String get fileSaveTranslation => 'Сохранить перевод…';

  @override
  String get fileSaveBoth => 'Сохранить оба…';

  @override
  String get fileExit => 'Выход';

  @override
  String get moreMenu => 'Ещё ▾';

  @override
  String get streamingToggle => 'Потоковый перевод';

  @override
  String get scrollSyncToggle => 'Синхронизация прокрутки';

  @override
  String get translate => 'Перевести';

  @override
  String get stop => 'Стоп';

  @override
  String get settingsTitle => 'Настройки';

  @override
  String get swapLanguages => 'Поменять языки';

  @override
  String get expandPanel => 'На всю ширину';

  @override
  String get paste => 'Вставить';

  @override
  String get clear => 'Очистить';

  @override
  String get copy => 'Копировать';

  @override
  String get copyAndHide => 'Копир. и скрыть';

  @override
  String get langFrom => 'Откуда';

  @override
  String get langTo => 'Куда';

  @override
  String get langAuto => 'AUTO';

  @override
  String get detectedLangTooltip => 'Определённый язык → фактическая цель';

  @override
  String get pairOverrideTooltip =>
      'Направление только для этого текста. Повторный свап вернёт автовыбор.';

  @override
  String get engineRestarting => 'Движок перезапускается…';

  @override
  String get engineArgos => 'Argos';

  @override
  String get engineLlm => 'LLM';

  @override
  String get engineTabs => 'Движок перевода';

  @override
  String get argosIdle => 'Argos';

  @override
  String get argosBusy => 'Argos';

  @override
  String get argosDone => 'Argos ✓';

  @override
  String get argosError => 'Argos ошибка';

  @override
  String get llmIdle => 'LLM';

  @override
  String get llmBusy => 'LLM';

  @override
  String get llmDone => 'LLM ✓';

  @override
  String get llmError => 'LLM ошибка';

  @override
  String get llmConnected => '● LLM';

  @override
  String get llmNotConfigured => 'LLM не задан';

  @override
  String get llmConnectionError => 'LLM ошибка';

  @override
  String get retry => 'Повторить';

  @override
  String get installModels => 'Установить модели';

  @override
  String get noArgosModels => 'Нет моделей Argos';

  @override
  String get noArgosModelsHint =>
      'Установите пакет en↔ru, чтобы переводить офлайн.';

  @override
  String get sourcePlaceholder => 'Введите или вставьте текст';

  @override
  String get unsupportedFile => 'Этот тип файла не поддерживается';

  @override
  String get openFileFirst => 'Сначала откройте файл';

  @override
  String get noTranslationToSave => 'Нет перевода для сохранения';

  @override
  String get saved => 'Сохранено';

  @override
  String get noTranslationEngine => 'Нет движка перевода';

  @override
  String get installFailed => 'Не удалось установить модели';

  @override
  String get copied => 'Скопировано';

  @override
  String get largeFileWarnHint =>
      'Файл большой: автоперевод не запущен. Нажмите «Перевести» или «Повтор».';

  @override
  String charCount(int count) {
    return '$count симв.';
  }

  @override
  String progressArgos(int done, int total) {
    return 'Argos $done/$total';
  }

  @override
  String progressLlm(int done, int total) {
    return 'LLM $done/$total';
  }

  @override
  String get progressLlmBusy => 'LLM…';

  @override
  String get progressArgosBusy => 'Argos…';

  @override
  String get settingsOk => 'ОК';

  @override
  String get settingsApply => 'Применить';

  @override
  String get settingsCancel => 'Отмена';

  @override
  String get settingsSectionAppearance => 'Внешний вид';

  @override
  String get settingsSectionTranslation => 'Перевод';

  @override
  String get settingsSectionLlm => 'LLM';

  @override
  String get settingsSectionFiles => 'Файлы';

  @override
  String get settingsSectionArgos => 'Argos';

  @override
  String get settingsSectionBehavior => 'Поведение';

  @override
  String get settingsSectionAbout => 'О программе';

  @override
  String get settingsAppearanceIntro =>
      'Тема, масштаб текста и прозрачность окна.';

  @override
  String get settingsTranslationIntro =>
      'Потоковый перевод, задержки и кэш Argos.';

  @override
  String get settingsLlmIntro => 'Локальный сервер, OpenRouter или свой адрес.';

  @override
  String get settingsFilesIntro => 'Кодировка, суффиксы и лимиты файлов.';

  @override
  String get settingsArgosIntro =>
      'Офлайн-модели Argos, установка из комплекта и папка packages.';

  @override
  String get settingsBehaviorIntro => 'Трей, горячие клавиши и буфер обмена.';

  @override
  String get settingsAboutIntro =>
      'Версия, статус движков и пути к конфигурации.';

  @override
  String get settingsTheme => 'Тема';

  @override
  String get settingsThemeDark => 'Тёмная';

  @override
  String get settingsThemeLight => 'Светлая';

  @override
  String get settingsEditorFont => 'Шрифт полей';

  @override
  String get settingsFontSystem => 'Системный';

  @override
  String get settingsFontMono => 'Моноширинный';

  @override
  String get settingsFontScale => 'Размер текста в полях';

  @override
  String get settingsOpacity => 'Прозрачность';

  @override
  String get settingsScrollSyncHonest =>
      'Синхронизация прокрутки (приблизительно, если нет якорей абзацев)';

  @override
  String get settingsDebounceArgos => 'Задержка Argos (мс)';

  @override
  String get settingsDebounceLlm => 'Задержка LLM (мс)';

  @override
  String get settingsTranslationCache => 'Кэш переводов Argos (LRU, сессия)';

  @override
  String get settingsTranslationCacheSize => 'Размер кэша';

  @override
  String get settingsLlmEnabled => 'Использовать LLM-перевод';

  @override
  String get settingsLlmProvider => 'Провайдер';

  @override
  String get settingsServerUrl => 'Адрес сервера';

  @override
  String get settingsServerUrlHint => 'http://127.0.0.1:11434/v1';

  @override
  String get settingsApiKey => 'Ключ API';

  @override
  String get settingsApiKeyLocalHint => 'Для LOCAL ключ не нужен.';

  @override
  String get settingsLlmModel => 'Модель';

  @override
  String get settingsLlmModelHint => 'Имя модели на сервере';

  @override
  String get settingsLlmCheck => 'Проверить';

  @override
  String get settingsLlmLoadModels => 'Загрузить модели';

  @override
  String get settingsLlmCloudWarning => 'Текст уходит в облако.';

  @override
  String get settingsLlmAdvanced => 'Дополнительные параметры';

  @override
  String get settingsLlmTemperature => 'Температура';

  @override
  String get settingsLlmMaxTokens => 'Макс. токенов';

  @override
  String get settingsLlmTimeout => 'Таймаут (с)';

  @override
  String get settingsLlmStream => 'Потоковый ответ модели';

  @override
  String get settingsLlmSystemPrompt => 'Системный промпт';

  @override
  String get settingsLlmChunkMax => 'Размер блока (симв.)';

  @override
  String get settingsLlmFileChunkMax => 'Размер блока файла (симв.)';

  @override
  String get settingsLlmFileChunkContext =>
      'Контекст между блоками при переводе файлов';

  @override
  String get settingsLlmAuthHeader => 'Заголовок авторизации';

  @override
  String get settingsAuthAuto => 'Авто';

  @override
  String get settingsAuthBearer => 'Bearer';

  @override
  String get settingsAuthApiKey => 'api-key';

  @override
  String get settingsEnableLlmFirst => 'Сначала включите перевод LLM.';

  @override
  String get settingsLlmConnected => 'Соединение установлено';

  @override
  String get settingsLlmModelsEmpty => 'Список моделей пуст';

  @override
  String settingsLlmCheckFailed(String error) {
    return 'Не удалось подключиться: $error';
  }

  @override
  String get settingsOutputEncoding => 'Кодировка выхода';

  @override
  String get settingsEncodingSame => 'Как у исходника';

  @override
  String get settingsEncodingUtf8 => 'UTF-8';

  @override
  String get settingsEncodingUtf8Bom => 'UTF-8 с BOM';

  @override
  String get settingsFileSuffix => 'Суффикс файла';

  @override
  String get settingsMaxFileMb => 'Макс. размер (МБ)';

  @override
  String get settingsHotkeyAutoTranslate =>
      'Автоперевод при захвате до (симв.)';

  @override
  String get settingsLargeFileWarn => 'Предупреждение от (симв.)';

  @override
  String get settingsTranslateCodeBlocks => 'Переводить блоки кода';

  @override
  String get settingsBundleOnStart =>
      'Устанавливать модели из комплекта при старте';

  @override
  String get settingsPreferApi => 'Предпочитать Python API';

  @override
  String get settingsPackagesDir => 'Папка моделей:';

  @override
  String get settingsPackagesUnknown => 'нет связи';

  @override
  String get settingsOpenPackages => 'Открыть packages';

  @override
  String get settingsInstallBundle => 'Установить комплект';

  @override
  String get settingsInstallArgosModel => 'Установить .argosmodel';

  @override
  String get settingsArgosCatalog =>
      'Дополнительные модели: argosopentech.com/argospm/';

  @override
  String get settingsCloseAction => 'При закрытии';

  @override
  String get settingsCloseTray => 'Сворачивать в трей';

  @override
  String get settingsCloseExit => 'Выходить';

  @override
  String get settingsGlobalHotkey => 'Глобальный хоткей';

  @override
  String get settingsHotkeyUnassigned => 'Не назначен';

  @override
  String get settingsHotkeyInvalid =>
      'Хоткей не распознан. Ctrl+C нельзя перехватывать — поле очищено.';

  @override
  String get settingsStartMinimized => 'Запускать свёрнутым в трей';

  @override
  String get settingsRestoreClipboard => 'Восстанавливать буфер после захвата';

  @override
  String get settingsCopyHideTray => 'Копировать и скрыть — сворачивать в трей';

  @override
  String get settingsTripleCopy =>
      'Тройной Ctrl+C вставляет выделенный текст и переводит';

  @override
  String get settingsArgosAvailable => 'Argos: доступен';

  @override
  String get settingsArgosNoModels => 'Argos: нет моделей';

  @override
  String get settingsArgosOffline => 'Argos: нет связи';

  @override
  String get settingsLlmOn => 'LLM: включён';

  @override
  String get settingsLlmOff => 'LLM: выключен';

  @override
  String get settingsPathLabel => 'Настройки:';

  @override
  String settingsModelsInstalled(int count) {
    return 'Установлено моделей: $count';
  }

  @override
  String get settingsPickerTitle => 'Выберите модель';

  @override
  String get settingsPickerSearch => 'Поиск';

  @override
  String get settingsPickerCancel => 'Отмена';

  @override
  String get settingsPickerSelect => 'Выбрать';

  @override
  String get firstRunTitle => 'Добро пожаловать';

  @override
  String get firstRunSubtitle =>
      'Четыре шага, чтобы начать перевод без облака.';

  @override
  String get firstRunStepTheme => 'Тема';

  @override
  String get firstRunStepModels => 'Модели Argos';

  @override
  String get firstRunStepLlm => 'LLM опционально';

  @override
  String get firstRunStepTray => 'Закрытие в трей';

  @override
  String get firstRunModelsHint => 'Установить комплект английский ↔ русский.';

  @override
  String get firstRunContinue => 'Далее';

  @override
  String get firstRunSkip => 'Пропустить';

  @override
  String get firstRunDone => 'Готово';
}
