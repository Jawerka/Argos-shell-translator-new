import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ru.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ru')
  ];

  /// No description provided for @appTitle.
  ///
  /// In ru, this message translates to:
  /// **'Argos Translate'**
  String get appTitle;

  /// No description provided for @trayShow.
  ///
  /// In ru, this message translates to:
  /// **'Показать'**
  String get trayShow;

  /// No description provided for @trayExit.
  ///
  /// In ru, this message translates to:
  /// **'Выход'**
  String get trayExit;

  /// No description provided for @bootFailedTitle.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось запустить'**
  String get bootFailedTitle;

  /// No description provided for @openLog.
  ///
  /// In ru, this message translates to:
  /// **'Открыть лог'**
  String get openLog;

  /// No description provided for @statusReady.
  ///
  /// In ru, this message translates to:
  /// **'Готово'**
  String get statusReady;

  /// No description provided for @sourcePanelTitle.
  ///
  /// In ru, this message translates to:
  /// **'Исходный текст'**
  String get sourcePanelTitle;

  /// No description provided for @translationPanelTitle.
  ///
  /// In ru, this message translates to:
  /// **'Перевод'**
  String get translationPanelTitle;

  /// No description provided for @emptyTranslationHint.
  ///
  /// In ru, this message translates to:
  /// **'Введите текст слева'**
  String get emptyTranslationHint;

  /// No description provided for @loading.
  ///
  /// In ru, this message translates to:
  /// **'Загрузка…'**
  String get loading;

  /// No description provided for @fileMenu.
  ///
  /// In ru, this message translates to:
  /// **'Файл'**
  String get fileMenu;

  /// No description provided for @fileOpen.
  ///
  /// In ru, this message translates to:
  /// **'Открыть…'**
  String get fileOpen;

  /// No description provided for @fileSaveTranslation.
  ///
  /// In ru, this message translates to:
  /// **'Сохранить перевод…'**
  String get fileSaveTranslation;

  /// No description provided for @fileSaveBoth.
  ///
  /// In ru, this message translates to:
  /// **'Сохранить оба…'**
  String get fileSaveBoth;

  /// No description provided for @fileExit.
  ///
  /// In ru, this message translates to:
  /// **'Выход'**
  String get fileExit;

  /// No description provided for @moreMenu.
  ///
  /// In ru, this message translates to:
  /// **'Ещё ▾'**
  String get moreMenu;

  /// No description provided for @streamingToggle.
  ///
  /// In ru, this message translates to:
  /// **'Потоковый перевод'**
  String get streamingToggle;

  /// No description provided for @scrollSyncToggle.
  ///
  /// In ru, this message translates to:
  /// **'Синхронизация прокрутки'**
  String get scrollSyncToggle;

  /// No description provided for @translate.
  ///
  /// In ru, this message translates to:
  /// **'Перевести'**
  String get translate;

  /// No description provided for @stop.
  ///
  /// In ru, this message translates to:
  /// **'Стоп'**
  String get stop;

  /// No description provided for @settingsTitle.
  ///
  /// In ru, this message translates to:
  /// **'Настройки'**
  String get settingsTitle;

  /// No description provided for @swapLanguages.
  ///
  /// In ru, this message translates to:
  /// **'Поменять языки'**
  String get swapLanguages;

  /// No description provided for @expandPanel.
  ///
  /// In ru, this message translates to:
  /// **'На всю ширину'**
  String get expandPanel;

  /// No description provided for @paste.
  ///
  /// In ru, this message translates to:
  /// **'Вставить'**
  String get paste;

  /// No description provided for @clear.
  ///
  /// In ru, this message translates to:
  /// **'Очистить'**
  String get clear;

  /// No description provided for @copy.
  ///
  /// In ru, this message translates to:
  /// **'Копировать'**
  String get copy;

  /// No description provided for @copyAndHide.
  ///
  /// In ru, this message translates to:
  /// **'Копир. и скрыть'**
  String get copyAndHide;

  /// No description provided for @langFrom.
  ///
  /// In ru, this message translates to:
  /// **'Откуда'**
  String get langFrom;

  /// No description provided for @langTo.
  ///
  /// In ru, this message translates to:
  /// **'Куда'**
  String get langTo;

  /// No description provided for @langAuto.
  ///
  /// In ru, this message translates to:
  /// **'AUTO'**
  String get langAuto;

  /// No description provided for @detectedLangTooltip.
  ///
  /// In ru, this message translates to:
  /// **'Определён язык исходника'**
  String get detectedLangTooltip;

  /// No description provided for @engineArgos.
  ///
  /// In ru, this message translates to:
  /// **'Argos'**
  String get engineArgos;

  /// No description provided for @engineLlm.
  ///
  /// In ru, this message translates to:
  /// **'LLM'**
  String get engineLlm;

  /// No description provided for @engineTabs.
  ///
  /// In ru, this message translates to:
  /// **'Движок перевода'**
  String get engineTabs;

  /// No description provided for @argosIdle.
  ///
  /// In ru, this message translates to:
  /// **'Argos'**
  String get argosIdle;

  /// No description provided for @argosBusy.
  ///
  /// In ru, this message translates to:
  /// **'Argos'**
  String get argosBusy;

  /// No description provided for @argosDone.
  ///
  /// In ru, this message translates to:
  /// **'Argos ✓'**
  String get argosDone;

  /// No description provided for @argosError.
  ///
  /// In ru, this message translates to:
  /// **'Argos ошибка'**
  String get argosError;

  /// No description provided for @llmIdle.
  ///
  /// In ru, this message translates to:
  /// **'LLM'**
  String get llmIdle;

  /// No description provided for @llmBusy.
  ///
  /// In ru, this message translates to:
  /// **'LLM'**
  String get llmBusy;

  /// No description provided for @llmDone.
  ///
  /// In ru, this message translates to:
  /// **'LLM ✓'**
  String get llmDone;

  /// No description provided for @llmError.
  ///
  /// In ru, this message translates to:
  /// **'LLM ошибка'**
  String get llmError;

  /// No description provided for @llmConnected.
  ///
  /// In ru, this message translates to:
  /// **'● LLM'**
  String get llmConnected;

  /// No description provided for @llmNotConfigured.
  ///
  /// In ru, this message translates to:
  /// **'LLM не задан'**
  String get llmNotConfigured;

  /// No description provided for @llmConnectionError.
  ///
  /// In ru, this message translates to:
  /// **'LLM ошибка'**
  String get llmConnectionError;

  /// No description provided for @retry.
  ///
  /// In ru, this message translates to:
  /// **'Повторить'**
  String get retry;

  /// No description provided for @installModels.
  ///
  /// In ru, this message translates to:
  /// **'Установить модели'**
  String get installModels;

  /// No description provided for @noArgosModels.
  ///
  /// In ru, this message translates to:
  /// **'Нет моделей Argos'**
  String get noArgosModels;

  /// No description provided for @noArgosModelsHint.
  ///
  /// In ru, this message translates to:
  /// **'Установите пакет en↔ru, чтобы переводить офлайн.'**
  String get noArgosModelsHint;

  /// No description provided for @sourcePlaceholder.
  ///
  /// In ru, this message translates to:
  /// **'Введите или вставьте текст'**
  String get sourcePlaceholder;

  /// No description provided for @unsupportedFile.
  ///
  /// In ru, this message translates to:
  /// **'Этот тип файла не поддерживается'**
  String get unsupportedFile;

  /// No description provided for @openFileFirst.
  ///
  /// In ru, this message translates to:
  /// **'Сначала откройте файл'**
  String get openFileFirst;

  /// No description provided for @noTranslationToSave.
  ///
  /// In ru, this message translates to:
  /// **'Нет перевода для сохранения'**
  String get noTranslationToSave;

  /// No description provided for @saved.
  ///
  /// In ru, this message translates to:
  /// **'Сохранено'**
  String get saved;

  /// No description provided for @noTranslationEngine.
  ///
  /// In ru, this message translates to:
  /// **'Нет движка перевода'**
  String get noTranslationEngine;

  /// No description provided for @installFailed.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось установить модели'**
  String get installFailed;

  /// No description provided for @copied.
  ///
  /// In ru, this message translates to:
  /// **'Скопировано'**
  String get copied;

  /// No description provided for @largeFileWarnHint.
  ///
  /// In ru, this message translates to:
  /// **'Файл большой: автоперевод не запущен. Нажмите «Перевести» или «Повтор».'**
  String get largeFileWarnHint;

  /// No description provided for @charCount.
  ///
  /// In ru, this message translates to:
  /// **'{count} симв.'**
  String charCount(int count);

  /// No description provided for @progressArgos.
  ///
  /// In ru, this message translates to:
  /// **'Argos {done}/{total}'**
  String progressArgos(int done, int total);

  /// No description provided for @progressLlm.
  ///
  /// In ru, this message translates to:
  /// **'LLM {done}/{total}'**
  String progressLlm(int done, int total);

  /// No description provided for @progressLlmBusy.
  ///
  /// In ru, this message translates to:
  /// **'LLM…'**
  String get progressLlmBusy;

  /// No description provided for @progressArgosBusy.
  ///
  /// In ru, this message translates to:
  /// **'Argos…'**
  String get progressArgosBusy;

  /// No description provided for @settingsOk.
  ///
  /// In ru, this message translates to:
  /// **'ОК'**
  String get settingsOk;

  /// No description provided for @settingsApply.
  ///
  /// In ru, this message translates to:
  /// **'Применить'**
  String get settingsApply;

  /// No description provided for @settingsCancel.
  ///
  /// In ru, this message translates to:
  /// **'Отмена'**
  String get settingsCancel;

  /// No description provided for @settingsSectionAppearance.
  ///
  /// In ru, this message translates to:
  /// **'Внешний вид'**
  String get settingsSectionAppearance;

  /// No description provided for @settingsSectionTranslation.
  ///
  /// In ru, this message translates to:
  /// **'Перевод'**
  String get settingsSectionTranslation;

  /// No description provided for @settingsSectionLlm.
  ///
  /// In ru, this message translates to:
  /// **'LLM'**
  String get settingsSectionLlm;

  /// No description provided for @settingsSectionFiles.
  ///
  /// In ru, this message translates to:
  /// **'Файлы'**
  String get settingsSectionFiles;

  /// No description provided for @settingsSectionArgos.
  ///
  /// In ru, this message translates to:
  /// **'Argos'**
  String get settingsSectionArgos;

  /// No description provided for @settingsSectionBehavior.
  ///
  /// In ru, this message translates to:
  /// **'Поведение'**
  String get settingsSectionBehavior;

  /// No description provided for @settingsSectionAbout.
  ///
  /// In ru, this message translates to:
  /// **'О программе'**
  String get settingsSectionAbout;

  /// No description provided for @settingsAppearanceIntro.
  ///
  /// In ru, this message translates to:
  /// **'Тема, масштаб текста и прозрачность окна.'**
  String get settingsAppearanceIntro;

  /// No description provided for @settingsTranslationIntro.
  ///
  /// In ru, this message translates to:
  /// **'Потоковый перевод, задержки и кэш Argos.'**
  String get settingsTranslationIntro;

  /// No description provided for @settingsLlmIntro.
  ///
  /// In ru, this message translates to:
  /// **'Локальный сервер, OpenRouter или свой адрес.'**
  String get settingsLlmIntro;

  /// No description provided for @settingsFilesIntro.
  ///
  /// In ru, this message translates to:
  /// **'Кодировка, суффиксы и лимиты файлов.'**
  String get settingsFilesIntro;

  /// No description provided for @settingsArgosIntro.
  ///
  /// In ru, this message translates to:
  /// **'Офлайн-модели Argos, установка из комплекта и папка packages.'**
  String get settingsArgosIntro;

  /// No description provided for @settingsBehaviorIntro.
  ///
  /// In ru, this message translates to:
  /// **'Трей, горячие клавиши и буфер обмена.'**
  String get settingsBehaviorIntro;

  /// No description provided for @settingsAboutIntro.
  ///
  /// In ru, this message translates to:
  /// **'Версия, статус движков и пути к конфигурации.'**
  String get settingsAboutIntro;

  /// No description provided for @settingsTheme.
  ///
  /// In ru, this message translates to:
  /// **'Тема'**
  String get settingsTheme;

  /// No description provided for @settingsThemeDark.
  ///
  /// In ru, this message translates to:
  /// **'Тёмная'**
  String get settingsThemeDark;

  /// No description provided for @settingsThemeLight.
  ///
  /// In ru, this message translates to:
  /// **'Светлая'**
  String get settingsThemeLight;

  /// No description provided for @settingsEditorFont.
  ///
  /// In ru, this message translates to:
  /// **'Шрифт полей'**
  String get settingsEditorFont;

  /// No description provided for @settingsFontSystem.
  ///
  /// In ru, this message translates to:
  /// **'Системный'**
  String get settingsFontSystem;

  /// No description provided for @settingsFontMono.
  ///
  /// In ru, this message translates to:
  /// **'Моноширинный'**
  String get settingsFontMono;

  /// No description provided for @settingsFontScale.
  ///
  /// In ru, this message translates to:
  /// **'Размер текста в полях'**
  String get settingsFontScale;

  /// No description provided for @settingsOpacity.
  ///
  /// In ru, this message translates to:
  /// **'Прозрачность'**
  String get settingsOpacity;

  /// No description provided for @settingsScrollSyncHonest.
  ///
  /// In ru, this message translates to:
  /// **'Синхронизация прокрутки (приблизительно, если нет якорей абзацев)'**
  String get settingsScrollSyncHonest;

  /// No description provided for @settingsDebounceArgos.
  ///
  /// In ru, this message translates to:
  /// **'Задержка Argos (мс)'**
  String get settingsDebounceArgos;

  /// No description provided for @settingsDebounceLlm.
  ///
  /// In ru, this message translates to:
  /// **'Задержка LLM (мс)'**
  String get settingsDebounceLlm;

  /// No description provided for @settingsTranslationCache.
  ///
  /// In ru, this message translates to:
  /// **'Кэш переводов Argos (LRU, сессия)'**
  String get settingsTranslationCache;

  /// No description provided for @settingsTranslationCacheSize.
  ///
  /// In ru, this message translates to:
  /// **'Размер кэша'**
  String get settingsTranslationCacheSize;

  /// No description provided for @settingsLlmEnabled.
  ///
  /// In ru, this message translates to:
  /// **'Использовать LLM-перевод'**
  String get settingsLlmEnabled;

  /// No description provided for @settingsLlmProvider.
  ///
  /// In ru, this message translates to:
  /// **'Провайдер'**
  String get settingsLlmProvider;

  /// No description provided for @settingsServerUrl.
  ///
  /// In ru, this message translates to:
  /// **'Адрес сервера'**
  String get settingsServerUrl;

  /// No description provided for @settingsServerUrlHint.
  ///
  /// In ru, this message translates to:
  /// **'http://127.0.0.1:11434/v1'**
  String get settingsServerUrlHint;

  /// No description provided for @settingsApiKey.
  ///
  /// In ru, this message translates to:
  /// **'Ключ API'**
  String get settingsApiKey;

  /// No description provided for @settingsApiKeyLocalHint.
  ///
  /// In ru, this message translates to:
  /// **'Для LOCAL ключ не нужен.'**
  String get settingsApiKeyLocalHint;

  /// No description provided for @settingsLlmModel.
  ///
  /// In ru, this message translates to:
  /// **'Модель'**
  String get settingsLlmModel;

  /// No description provided for @settingsLlmModelHint.
  ///
  /// In ru, this message translates to:
  /// **'Имя модели на сервере'**
  String get settingsLlmModelHint;

  /// No description provided for @settingsLlmCheck.
  ///
  /// In ru, this message translates to:
  /// **'Проверить'**
  String get settingsLlmCheck;

  /// No description provided for @settingsLlmLoadModels.
  ///
  /// In ru, this message translates to:
  /// **'Загрузить модели'**
  String get settingsLlmLoadModels;

  /// No description provided for @settingsLlmCloudWarning.
  ///
  /// In ru, this message translates to:
  /// **'Текст уходит в облако.'**
  String get settingsLlmCloudWarning;

  /// No description provided for @settingsLlmAdvanced.
  ///
  /// In ru, this message translates to:
  /// **'Дополнительные параметры'**
  String get settingsLlmAdvanced;

  /// No description provided for @settingsLlmTemperature.
  ///
  /// In ru, this message translates to:
  /// **'Температура'**
  String get settingsLlmTemperature;

  /// No description provided for @settingsLlmMaxTokens.
  ///
  /// In ru, this message translates to:
  /// **'Макс. токенов'**
  String get settingsLlmMaxTokens;

  /// No description provided for @settingsLlmTimeout.
  ///
  /// In ru, this message translates to:
  /// **'Таймаут (с)'**
  String get settingsLlmTimeout;

  /// No description provided for @settingsLlmStream.
  ///
  /// In ru, this message translates to:
  /// **'Потоковый ответ модели'**
  String get settingsLlmStream;

  /// No description provided for @settingsLlmSystemPrompt.
  ///
  /// In ru, this message translates to:
  /// **'Системный промпт'**
  String get settingsLlmSystemPrompt;

  /// No description provided for @settingsLlmChunkMax.
  ///
  /// In ru, this message translates to:
  /// **'Размер блока (симв.)'**
  String get settingsLlmChunkMax;

  /// No description provided for @settingsLlmFileChunkMax.
  ///
  /// In ru, this message translates to:
  /// **'Размер блока файла (симв.)'**
  String get settingsLlmFileChunkMax;

  /// No description provided for @settingsLlmFileChunkContext.
  ///
  /// In ru, this message translates to:
  /// **'Контекст между блоками при переводе файлов'**
  String get settingsLlmFileChunkContext;

  /// No description provided for @settingsLlmAuthHeader.
  ///
  /// In ru, this message translates to:
  /// **'Заголовок авторизации'**
  String get settingsLlmAuthHeader;

  /// No description provided for @settingsAuthAuto.
  ///
  /// In ru, this message translates to:
  /// **'Авто'**
  String get settingsAuthAuto;

  /// No description provided for @settingsAuthBearer.
  ///
  /// In ru, this message translates to:
  /// **'Bearer'**
  String get settingsAuthBearer;

  /// No description provided for @settingsAuthApiKey.
  ///
  /// In ru, this message translates to:
  /// **'api-key'**
  String get settingsAuthApiKey;

  /// No description provided for @settingsEnableLlmFirst.
  ///
  /// In ru, this message translates to:
  /// **'Сначала включите перевод LLM.'**
  String get settingsEnableLlmFirst;

  /// No description provided for @settingsLlmConnected.
  ///
  /// In ru, this message translates to:
  /// **'Соединение установлено'**
  String get settingsLlmConnected;

  /// No description provided for @settingsLlmModelsEmpty.
  ///
  /// In ru, this message translates to:
  /// **'Список моделей пуст'**
  String get settingsLlmModelsEmpty;

  /// No description provided for @settingsLlmCheckFailed.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось подключиться: {error}'**
  String settingsLlmCheckFailed(String error);

  /// No description provided for @settingsOutputEncoding.
  ///
  /// In ru, this message translates to:
  /// **'Кодировка выхода'**
  String get settingsOutputEncoding;

  /// No description provided for @settingsEncodingSame.
  ///
  /// In ru, this message translates to:
  /// **'Как у исходника'**
  String get settingsEncodingSame;

  /// No description provided for @settingsEncodingUtf8.
  ///
  /// In ru, this message translates to:
  /// **'UTF-8'**
  String get settingsEncodingUtf8;

  /// No description provided for @settingsEncodingUtf8Bom.
  ///
  /// In ru, this message translates to:
  /// **'UTF-8 с BOM'**
  String get settingsEncodingUtf8Bom;

  /// No description provided for @settingsFileSuffix.
  ///
  /// In ru, this message translates to:
  /// **'Суффикс файла'**
  String get settingsFileSuffix;

  /// No description provided for @settingsMaxFileMb.
  ///
  /// In ru, this message translates to:
  /// **'Макс. размер (МБ)'**
  String get settingsMaxFileMb;

  /// No description provided for @settingsHotkeyAutoTranslate.
  ///
  /// In ru, this message translates to:
  /// **'Автоперевод при захвате до (симв.)'**
  String get settingsHotkeyAutoTranslate;

  /// No description provided for @settingsLargeFileWarn.
  ///
  /// In ru, this message translates to:
  /// **'Предупреждение от (симв.)'**
  String get settingsLargeFileWarn;

  /// No description provided for @settingsTranslateCodeBlocks.
  ///
  /// In ru, this message translates to:
  /// **'Переводить блоки кода'**
  String get settingsTranslateCodeBlocks;

  /// No description provided for @settingsBundleOnStart.
  ///
  /// In ru, this message translates to:
  /// **'Устанавливать модели из комплекта при старте'**
  String get settingsBundleOnStart;

  /// No description provided for @settingsPreferApi.
  ///
  /// In ru, this message translates to:
  /// **'Предпочитать Python API'**
  String get settingsPreferApi;

  /// No description provided for @settingsPackagesDir.
  ///
  /// In ru, this message translates to:
  /// **'Папка моделей:'**
  String get settingsPackagesDir;

  /// No description provided for @settingsPackagesUnknown.
  ///
  /// In ru, this message translates to:
  /// **'нет связи'**
  String get settingsPackagesUnknown;

  /// No description provided for @settingsOpenPackages.
  ///
  /// In ru, this message translates to:
  /// **'Открыть packages'**
  String get settingsOpenPackages;

  /// No description provided for @settingsInstallBundle.
  ///
  /// In ru, this message translates to:
  /// **'Установить комплект'**
  String get settingsInstallBundle;

  /// No description provided for @settingsInstallArgosModel.
  ///
  /// In ru, this message translates to:
  /// **'Установить .argosmodel'**
  String get settingsInstallArgosModel;

  /// No description provided for @settingsArgosCatalog.
  ///
  /// In ru, this message translates to:
  /// **'Дополнительные модели: argosopentech.com/argospm/'**
  String get settingsArgosCatalog;

  /// No description provided for @settingsCloseAction.
  ///
  /// In ru, this message translates to:
  /// **'При закрытии'**
  String get settingsCloseAction;

  /// No description provided for @settingsCloseTray.
  ///
  /// In ru, this message translates to:
  /// **'Сворачивать в трей'**
  String get settingsCloseTray;

  /// No description provided for @settingsCloseExit.
  ///
  /// In ru, this message translates to:
  /// **'Выходить'**
  String get settingsCloseExit;

  /// No description provided for @settingsGlobalHotkey.
  ///
  /// In ru, this message translates to:
  /// **'Глобальный хоткей'**
  String get settingsGlobalHotkey;

  /// No description provided for @settingsHotkeyUnassigned.
  ///
  /// In ru, this message translates to:
  /// **'Не назначен'**
  String get settingsHotkeyUnassigned;

  /// No description provided for @settingsHotkeyInvalid.
  ///
  /// In ru, this message translates to:
  /// **'Хоткей не распознан. Ctrl+C нельзя перехватывать — поле очищено.'**
  String get settingsHotkeyInvalid;

  /// No description provided for @settingsStartMinimized.
  ///
  /// In ru, this message translates to:
  /// **'Запускать свёрнутым в трей'**
  String get settingsStartMinimized;

  /// No description provided for @settingsRestoreClipboard.
  ///
  /// In ru, this message translates to:
  /// **'Восстанавливать буфер после захвата'**
  String get settingsRestoreClipboard;

  /// No description provided for @settingsCopyHideTray.
  ///
  /// In ru, this message translates to:
  /// **'Копировать и скрыть — сворачивать в трей'**
  String get settingsCopyHideTray;

  /// No description provided for @settingsArgosAvailable.
  ///
  /// In ru, this message translates to:
  /// **'Argos: доступен'**
  String get settingsArgosAvailable;

  /// No description provided for @settingsArgosNoModels.
  ///
  /// In ru, this message translates to:
  /// **'Argos: нет моделей'**
  String get settingsArgosNoModels;

  /// No description provided for @settingsArgosOffline.
  ///
  /// In ru, this message translates to:
  /// **'Argos: нет связи'**
  String get settingsArgosOffline;

  /// No description provided for @settingsLlmOn.
  ///
  /// In ru, this message translates to:
  /// **'LLM: включён'**
  String get settingsLlmOn;

  /// No description provided for @settingsLlmOff.
  ///
  /// In ru, this message translates to:
  /// **'LLM: выключен'**
  String get settingsLlmOff;

  /// No description provided for @settingsPathLabel.
  ///
  /// In ru, this message translates to:
  /// **'Настройки:'**
  String get settingsPathLabel;

  /// No description provided for @settingsModelsInstalled.
  ///
  /// In ru, this message translates to:
  /// **'Установлено моделей: {count}'**
  String settingsModelsInstalled(int count);

  /// No description provided for @settingsPickerTitle.
  ///
  /// In ru, this message translates to:
  /// **'Выберите модель'**
  String get settingsPickerTitle;

  /// No description provided for @settingsPickerSearch.
  ///
  /// In ru, this message translates to:
  /// **'Поиск'**
  String get settingsPickerSearch;

  /// No description provided for @settingsPickerCancel.
  ///
  /// In ru, this message translates to:
  /// **'Отмена'**
  String get settingsPickerCancel;

  /// No description provided for @settingsPickerSelect.
  ///
  /// In ru, this message translates to:
  /// **'Выбрать'**
  String get settingsPickerSelect;

  /// No description provided for @firstRunTitle.
  ///
  /// In ru, this message translates to:
  /// **'Добро пожаловать'**
  String get firstRunTitle;

  /// No description provided for @firstRunSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Четыре шага, чтобы начать перевод без облака.'**
  String get firstRunSubtitle;

  /// No description provided for @firstRunStepTheme.
  ///
  /// In ru, this message translates to:
  /// **'Тема'**
  String get firstRunStepTheme;

  /// No description provided for @firstRunStepModels.
  ///
  /// In ru, this message translates to:
  /// **'Модели Argos'**
  String get firstRunStepModels;

  /// No description provided for @firstRunStepLlm.
  ///
  /// In ru, this message translates to:
  /// **'LLM опционально'**
  String get firstRunStepLlm;

  /// No description provided for @firstRunStepTray.
  ///
  /// In ru, this message translates to:
  /// **'Закрытие в трей'**
  String get firstRunStepTray;

  /// No description provided for @firstRunModelsHint.
  ///
  /// In ru, this message translates to:
  /// **'Установить комплект английский ↔ русский.'**
  String get firstRunModelsHint;

  /// No description provided for @firstRunContinue.
  ///
  /// In ru, this message translates to:
  /// **'Далее'**
  String get firstRunContinue;

  /// No description provided for @firstRunSkip.
  ///
  /// In ru, this message translates to:
  /// **'Пропустить'**
  String get firstRunSkip;

  /// No description provided for @firstRunDone.
  ///
  /// In ru, this message translates to:
  /// **'Готово'**
  String get firstRunDone;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ru'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ru':
      return AppLocalizationsRu();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
