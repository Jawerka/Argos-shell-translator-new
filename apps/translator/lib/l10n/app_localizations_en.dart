// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Argos Translate';

  @override
  String get trayShow => 'Show';

  @override
  String get trayExit => 'Exit';

  @override
  String get bootFailedTitle => 'Failed to start';

  @override
  String get openLog => 'Open log';

  @override
  String get statusReady => 'Ready';

  @override
  String get sourcePanelTitle => 'Source text';

  @override
  String get translationPanelTitle => 'Translation';

  @override
  String get emptyTranslationHint => 'Type text on the left';

  @override
  String get loading => 'Loading…';

  @override
  String get fileMenu => 'File';

  @override
  String get fileOpen => 'Open…';

  @override
  String get fileSaveTranslation => 'Save translation…';

  @override
  String get fileSaveBoth => 'Save both…';

  @override
  String get fileExit => 'Exit';

  @override
  String get moreMenu => 'More ▾';

  @override
  String get streamingToggle => 'Translate as you type';

  @override
  String get scrollSyncToggle => 'Scroll sync';

  @override
  String get translate => 'Translate';

  @override
  String get stop => 'Stop';

  @override
  String get settingsTitle => 'Settings';

  @override
  String get swapLanguages => 'Swap languages';

  @override
  String get expandPanel => 'Full width';

  @override
  String get paste => 'Paste';

  @override
  String get clear => 'Clear';

  @override
  String get copy => 'Copy';

  @override
  String get copyAndHide => 'Copy & hide';

  @override
  String get langFrom => 'From';

  @override
  String get langTo => 'To';

  @override
  String get langAuto => 'AUTO';

  @override
  String get detectedLangTooltip => 'Detected language → actual target';

  @override
  String get engineRestarting => 'Engine is restarting…';

  @override
  String get engineArgos => 'Argos';

  @override
  String get engineLlm => 'LLM';

  @override
  String get engineTabs => 'Translation engine';

  @override
  String get argosIdle => 'Argos';

  @override
  String get argosBusy => 'Argos';

  @override
  String get argosDone => 'Argos ✓';

  @override
  String get argosError => 'Argos error';

  @override
  String get llmIdle => 'LLM';

  @override
  String get llmBusy => 'LLM';

  @override
  String get llmDone => 'LLM ✓';

  @override
  String get llmError => 'LLM error';

  @override
  String get llmConnected => '● LLM';

  @override
  String get llmNotConfigured => 'LLM not set';

  @override
  String get llmConnectionError => 'LLM error';

  @override
  String get retry => 'Retry';

  @override
  String get installModels => 'Install models';

  @override
  String get noArgosModels => 'No Argos models';

  @override
  String get noArgosModelsHint =>
      'Install the en↔ru pack to translate offline.';

  @override
  String get sourcePlaceholder => 'Type or paste text';

  @override
  String get unsupportedFile => 'This file type is not supported';

  @override
  String get openFileFirst => 'Open a file first';

  @override
  String get noTranslationToSave => 'Nothing to save';

  @override
  String get saved => 'Saved';

  @override
  String get noTranslationEngine => 'Translation engine is unavailable';

  @override
  String get installFailed => 'Could not install models';

  @override
  String get copied => 'Copied';

  @override
  String get largeFileWarnHint =>
      'Large file: auto-translate was skipped. Press Translate or Retry.';

  @override
  String charCount(int count) {
    return '$count ch.';
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
  String get settingsOk => 'OK';

  @override
  String get settingsApply => 'Apply';

  @override
  String get settingsCancel => 'Cancel';

  @override
  String get settingsSectionAppearance => 'Appearance';

  @override
  String get settingsSectionTranslation => 'Translation';

  @override
  String get settingsSectionLlm => 'LLM';

  @override
  String get settingsSectionFiles => 'Files';

  @override
  String get settingsSectionArgos => 'Argos';

  @override
  String get settingsSectionBehavior => 'Behavior';

  @override
  String get settingsSectionAbout => 'About';

  @override
  String get settingsAppearanceIntro =>
      'Theme, editor font and window opacity.';

  @override
  String get settingsTranslationIntro =>
      'Live translation, delays and Argos cache.';

  @override
  String get settingsLlmIntro =>
      'Local server, OpenRouter or a custom address.';

  @override
  String get settingsFilesIntro => 'Encoding, suffixes and file limits.';

  @override
  String get settingsArgosIntro =>
      'Offline Argos models, bundle install and packages folder.';

  @override
  String get settingsBehaviorIntro => 'Tray, shortcuts and clipboard.';

  @override
  String get settingsAboutIntro => 'Version, engine status and config paths.';

  @override
  String get settingsTheme => 'Theme';

  @override
  String get settingsThemeDark => 'Dark';

  @override
  String get settingsThemeLight => 'Light';

  @override
  String get settingsEditorFont => 'Editor font';

  @override
  String get settingsFontSystem => 'System';

  @override
  String get settingsFontMono => 'Monospace';

  @override
  String get settingsFontScale => 'Editor text size';

  @override
  String get settingsOpacity => 'Opacity';

  @override
  String get settingsScrollSyncHonest =>
      'Scroll sync (approximate if there are no paragraph anchors)';

  @override
  String get settingsDebounceArgos => 'Argos delay (ms)';

  @override
  String get settingsDebounceLlm => 'LLM delay (ms)';

  @override
  String get settingsTranslationCache =>
      'Argos translation cache for this session';

  @override
  String get settingsTranslationCacheSize => 'Cache size';

  @override
  String get settingsLlmEnabled => 'Use LLM translation';

  @override
  String get settingsLlmProvider => 'Provider';

  @override
  String get settingsServerUrl => 'Server address';

  @override
  String get settingsServerUrlHint => 'http://127.0.0.1:11434/v1';

  @override
  String get settingsApiKey => 'API key';

  @override
  String get settingsApiKeyLocalHint => 'LOCAL does not need a key.';

  @override
  String get settingsLlmModel => 'Model';

  @override
  String get settingsLlmModelHint => 'Model name on the server';

  @override
  String get settingsLlmCheck => 'Check';

  @override
  String get settingsLlmLoadModels => 'Load models';

  @override
  String get settingsLlmCloudWarning => 'Text is sent to the cloud.';

  @override
  String get settingsLlmAdvanced => 'Advanced parameters';

  @override
  String get settingsLlmTemperature => 'Temperature';

  @override
  String get settingsLlmMaxTokens => 'Max tokens';

  @override
  String get settingsLlmTimeout => 'Timeout (s)';

  @override
  String get settingsLlmStream => 'Stream model output';

  @override
  String get settingsLlmSystemPrompt => 'System prompt';

  @override
  String get settingsLlmChunkMax => 'Chunk size (chars)';

  @override
  String get settingsLlmFileChunkMax => 'File chunk size (chars)';

  @override
  String get settingsLlmFileChunkContext => 'Keep context between file chunks';

  @override
  String get settingsLlmAuthHeader => 'Auth header';

  @override
  String get settingsAuthAuto => 'Auto';

  @override
  String get settingsAuthBearer => 'Bearer';

  @override
  String get settingsAuthApiKey => 'api-key';

  @override
  String get settingsEnableLlmFirst => 'Turn on LLM translation first.';

  @override
  String get settingsLlmConnected => 'Connection established';

  @override
  String get settingsLlmModelsEmpty => 'The model list is empty';

  @override
  String settingsLlmCheckFailed(String error) {
    return 'Could not connect: $error';
  }

  @override
  String get settingsOutputEncoding => 'Output encoding';

  @override
  String get settingsEncodingSame => 'Same as source';

  @override
  String get settingsEncodingUtf8 => 'UTF-8';

  @override
  String get settingsEncodingUtf8Bom => 'UTF-8 with BOM';

  @override
  String get settingsFileSuffix => 'File suffix';

  @override
  String get settingsMaxFileMb => 'Max size (MB)';

  @override
  String get settingsHotkeyAutoTranslate =>
      'Auto-translate on capture up to (chars)';

  @override
  String get settingsLargeFileWarn => 'Warn from (chars)';

  @override
  String get settingsTranslateCodeBlocks => 'Translate code blocks';

  @override
  String get settingsBundleOnStart => 'Install bundled models on start';

  @override
  String get settingsPreferApi => 'Prefer Python API';

  @override
  String get settingsPackagesDir => 'Models folder:';

  @override
  String get settingsPackagesUnknown => 'no connection';

  @override
  String get settingsOpenPackages => 'Open packages';

  @override
  String get settingsInstallBundle => 'Install bundle';

  @override
  String get settingsInstallArgosModel => 'Install .argosmodel';

  @override
  String get settingsArgosCatalog => 'More models: argosopentech.com/argospm/';

  @override
  String get settingsCloseAction => 'On close';

  @override
  String get settingsCloseTray => 'Minimize to tray';

  @override
  String get settingsCloseExit => 'Exit';

  @override
  String get settingsGlobalHotkey => 'Global hotkey';

  @override
  String get settingsHotkeyUnassigned => 'Not assigned';

  @override
  String get settingsHotkeyInvalid =>
      'Hotkey is not valid. Ctrl+C cannot be captured — the field was cleared.';

  @override
  String get settingsStartMinimized => 'Start minimized to tray';

  @override
  String get settingsRestoreClipboard => 'Restore clipboard after capture';

  @override
  String get settingsCopyHideTray => 'Copy and hide — minimize to tray';

  @override
  String get settingsTripleCopy =>
      'Triple Ctrl+C pastes the copied text and translates';

  @override
  String get settingsArgosAvailable => 'Argos: available';

  @override
  String get settingsArgosNoModels => 'Argos: no models';

  @override
  String get settingsArgosOffline => 'Argos: no connection';

  @override
  String get settingsLlmOn => 'LLM: on';

  @override
  String get settingsLlmOff => 'LLM: off';

  @override
  String get settingsPathLabel => 'Settings:';

  @override
  String settingsModelsInstalled(int count) {
    return 'Models installed: $count';
  }

  @override
  String get settingsPickerTitle => 'Choose a model';

  @override
  String get settingsPickerSearch => 'Search';

  @override
  String get settingsPickerCancel => 'Cancel';

  @override
  String get settingsPickerSelect => 'Select';

  @override
  String get firstRunTitle => 'Welcome';

  @override
  String get firstRunSubtitle =>
      'Four steps to start translating without the cloud.';

  @override
  String get firstRunStepTheme => 'Theme';

  @override
  String get firstRunStepModels => 'Argos models';

  @override
  String get firstRunStepLlm => 'LLM (optional)';

  @override
  String get firstRunStepTray => 'Close to tray';

  @override
  String get firstRunModelsHint => 'Install the English ↔ Russian bundle.';

  @override
  String get firstRunContinue => 'Continue';

  @override
  String get firstRunSkip => 'Skip';

  @override
  String get firstRunDone => 'Готово';
}
