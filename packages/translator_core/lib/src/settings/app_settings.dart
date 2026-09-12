import '../json_util.dart';

const currentSettingsVersion = 9;

class BehaviorSettings {
  const BehaviorSettings({
    this.closeAction = 'tray',
    this.startMinimizedToTray = false,
    this.trayClickAction = 'show',
    this.restoreClipboardAfterCapture = true,
    this.globalHotkey = '',
    this.minimizeToTrayOnCopyHide = true,
    this.translationCacheEnabled = false,
    this.translationCacheSize = 500,
    this.tripleCopyEnabled = true,
  });

  final String closeAction;
  final bool startMinimizedToTray;
  final String trayClickAction;
  final bool restoreClipboardAfterCapture;
  final String globalHotkey;
  final bool minimizeToTrayOnCopyHide;
  final bool translationCacheEnabled;
  final int translationCacheSize;
  final bool tripleCopyEnabled;

  BehaviorSettings copyWith({
    String? closeAction,
    bool? startMinimizedToTray,
    String? trayClickAction,
    bool? restoreClipboardAfterCapture,
    String? globalHotkey,
    bool? minimizeToTrayOnCopyHide,
    bool? translationCacheEnabled,
    int? translationCacheSize,
    bool? tripleCopyEnabled,
  }) {
    return BehaviorSettings(
      closeAction: closeAction ?? this.closeAction,
      startMinimizedToTray: startMinimizedToTray ?? this.startMinimizedToTray,
      trayClickAction: trayClickAction ?? this.trayClickAction,
      restoreClipboardAfterCapture:
          restoreClipboardAfterCapture ?? this.restoreClipboardAfterCapture,
      globalHotkey: globalHotkey ?? this.globalHotkey,
      minimizeToTrayOnCopyHide:
          minimizeToTrayOnCopyHide ?? this.minimizeToTrayOnCopyHide,
      translationCacheEnabled:
          translationCacheEnabled ?? this.translationCacheEnabled,
      translationCacheSize: translationCacheSize ?? this.translationCacheSize,
      tripleCopyEnabled: tripleCopyEnabled ?? this.tripleCopyEnabled,
    );
  }
}

class FileSettings {
  const FileSettings({
    this.outputEncoding = 'same',
    this.outputSuffix = '_translated',
    this.maxFileSizeMb = 10,
    this.hotkeyAutoTranslateMaxChars = 500,
    this.largeFileWarnChars = 50000,
    this.translateCodeBlocks = false,
  });

  final String outputEncoding;
  final String outputSuffix;
  final int maxFileSizeMb;
  final int hotkeyAutoTranslateMaxChars;
  final int largeFileWarnChars;
  final bool translateCodeBlocks;

  FileSettings copyWith({
    String? outputEncoding,
    String? outputSuffix,
    int? maxFileSizeMb,
    int? hotkeyAutoTranslateMaxChars,
    int? largeFileWarnChars,
    bool? translateCodeBlocks,
  }) {
    return FileSettings(
      outputEncoding: outputEncoding ?? this.outputEncoding,
      outputSuffix: outputSuffix ?? this.outputSuffix,
      maxFileSizeMb: maxFileSizeMb ?? this.maxFileSizeMb,
      hotkeyAutoTranslateMaxChars:
          hotkeyAutoTranslateMaxChars ?? this.hotkeyAutoTranslateMaxChars,
      largeFileWarnChars: largeFileWarnChars ?? this.largeFileWarnChars,
      translateCodeBlocks: translateCodeBlocks ?? this.translateCodeBlocks,
    );
  }
}

class ArgosEngineSettings {
  const ArgosEngineSettings({
    this.packagesDir = '',
    this.preferApiOverCli = true,
    this.bundleModelsOnStart = true,
  });

  final String packagesDir;
  final bool preferApiOverCli;
  final bool bundleModelsOnStart;

  ArgosEngineSettings copyWith({
    String? packagesDir,
    bool? preferApiOverCli,
    bool? bundleModelsOnStart,
  }) {
    return ArgosEngineSettings(
      packagesDir: packagesDir ?? this.packagesDir,
      preferApiOverCli: preferApiOverCli ?? this.preferApiOverCli,
      bundleModelsOnStart: bundleModelsOnStart ?? this.bundleModelsOnStart,
    );
  }
}

class LlmSettings {
  const LlmSettings({
    this.enabled = true,
    this.provider = 'local',
    this.baseUrl = '',
    this.providerUrls = const {
      'local': '',
      'openrouter': 'https://openrouter.ai/api/v1',
      'custom': '',
    },
    this.apiKeys = const {'openrouter': '', 'custom': ''},
    this.apiKeyRefs = const {'openrouter': '', 'custom': ''},
    this.model = '',
    this.authHeader = 'auto',
    this.temperature = 0.3,
    this.maxTokens = 4096,
    this.timeoutSec = 120,
    this.stream = true,
    this.healthCheckTtlSec = 30,
    this.systemPrompt = '',
    this.chunkMaxChars = 6000,
    this.fileChunkMaxChars = 3500,
    this.fileChunkContext = true,
  });

  final bool enabled;
  final String provider;
  final String baseUrl;
  final Map<String, String> providerUrls;
  final Map<String, String> apiKeys;
  final Map<String, String> apiKeyRefs;
  final String model;
  final String authHeader;
  final double temperature;
  final int maxTokens;
  final int timeoutSec;
  final bool stream;
  final int healthCheckTtlSec;
  final String systemPrompt;
  final int chunkMaxChars;
  final int fileChunkMaxChars;
  final bool fileChunkContext;

  LlmSettings copyWith({
    bool? enabled,
    String? provider,
    String? baseUrl,
    Map<String, String>? providerUrls,
    Map<String, String>? apiKeys,
    Map<String, String>? apiKeyRefs,
    String? model,
    String? authHeader,
    double? temperature,
    int? maxTokens,
    int? timeoutSec,
    bool? stream,
    int? healthCheckTtlSec,
    String? systemPrompt,
    int? chunkMaxChars,
    int? fileChunkMaxChars,
    bool? fileChunkContext,
  }) {
    return LlmSettings(
      enabled: enabled ?? this.enabled,
      provider: provider ?? this.provider,
      baseUrl: baseUrl ?? this.baseUrl,
      providerUrls: Map<String, String>.from(providerUrls ?? this.providerUrls),
      apiKeys: Map<String, String>.from(apiKeys ?? this.apiKeys),
      apiKeyRefs: Map<String, String>.from(apiKeyRefs ?? this.apiKeyRefs),
      model: model ?? this.model,
      authHeader: authHeader ?? this.authHeader,
      temperature: temperature ?? this.temperature,
      maxTokens: maxTokens ?? this.maxTokens,
      timeoutSec: timeoutSec ?? this.timeoutSec,
      stream: stream ?? this.stream,
      healthCheckTtlSec: healthCheckTtlSec ?? this.healthCheckTtlSec,
      systemPrompt: systemPrompt ?? this.systemPrompt,
      chunkMaxChars: chunkMaxChars ?? this.chunkMaxChars,
      fileChunkMaxChars: fileChunkMaxChars ?? this.fileChunkMaxChars,
      fileChunkContext: fileChunkContext ?? this.fileChunkContext,
    );
  }
}

class WindowSettings {
  const WindowSettings({
    this.state = 'normal',
    this.x = 100,
    this.y = 100,
    this.width = 1000,
    this.height = 700,
    this.dpiScale = 1.0,
    this.geometryUnits = 'legacy',
    this.opacity = 1.0,
    this.theme = 'dark',
    this.fontScale = 1.0,
    this.editorLayout = 'split',
    this.editorFont = 'system',
    this.geometryLegacy,
    this.extras = const {},
  });

  final String state;
  final int x;
  final int y;
  final int width;
  final int height;
  final double dpiScale;
  final String geometryUnits;
  final double opacity;
  final String theme;
  final double fontScale;
  final String editorLayout;
  final String editorFont;
  final String? geometryLegacy;
  final Map<String, Object?> extras;

  WindowSettings copyWith({
    String? state,
    int? x,
    int? y,
    int? width,
    int? height,
    double? dpiScale,
    String? geometryUnits,
    double? opacity,
    String? theme,
    double? fontScale,
    String? editorLayout,
    String? editorFont,
    String? geometryLegacy,
    Map<String, Object?>? extras,
  }) {
    return WindowSettings(
      state: state ?? this.state,
      x: x ?? this.x,
      y: y ?? this.y,
      width: width ?? this.width,
      height: height ?? this.height,
      dpiScale: dpiScale ?? this.dpiScale,
      geometryUnits: geometryUnits ?? this.geometryUnits,
      opacity: opacity ?? this.opacity,
      theme: theme ?? this.theme,
      fontScale: fontScale ?? this.fontScale,
      editorLayout: editorLayout ?? this.editorLayout,
      editorFont: editorFont ?? this.editorFont,
      geometryLegacy: geometryLegacy ?? this.geometryLegacy,
      extras: Map<String, Object?>.from(extras ?? this.extras),
    );
  }
}

/// Настройки v9: `%USERPROFILE%\.argos_translate\settings.json`.
class AppSettings {
  const AppSettings({
    this.version = currentSettingsVersion,
    this.window = const WindowSettings(),
    this.streaming = true,
    this.scrollSync = true,
    this.debounceMs = 700,
    this.llmDebounceMs = 1200,
    this.autoTargetLang = 'ru',
    this.langFrom = 'auto',
    this.langTo = 'ru',
    this.llm = const LlmSettings(),
    this.files = const FileSettings(),
    this.argos = const ArgosEngineSettings(),
    this.behavior = const BehaviorSettings(),
    this.activeTranslationTab = 'argos',
    this.firstRunDone = false,
    this.defaultEngine = 'both_adaptive',
    this.uiExtras = const {},
    this.extras = const {},
  });

  final int version;
  final WindowSettings window;
  final bool streaming;
  final bool scrollSync;
  final int debounceMs;
  final int llmDebounceMs;
  final String autoTargetLang;
  final String langFrom;
  final String langTo;
  final LlmSettings llm;
  final FileSettings files;
  final ArgosEngineSettings argos;
  final BehaviorSettings behavior;
  final String activeTranslationTab;
  final bool firstRunDone;
  final String defaultEngine;
  final Map<String, Object?> uiExtras;
  final Map<String, Object?> extras;

  String get theme => window.theme;

  AppSettings copyWith({
    int? version,
    WindowSettings? window,
    bool? streaming,
    bool? scrollSync,
    int? debounceMs,
    int? llmDebounceMs,
    String? autoTargetLang,
    String? langFrom,
    String? langTo,
    LlmSettings? llm,
    FileSettings? files,
    ArgosEngineSettings? argos,
    BehaviorSettings? behavior,
    String? activeTranslationTab,
    bool? firstRunDone,
    String? defaultEngine,
    Map<String, Object?>? uiExtras,
    Map<String, Object?>? extras,
  }) {
    return AppSettings(
      version: version ?? this.version,
      window: window ?? this.window.copyWith(),
      streaming: streaming ?? this.streaming,
      scrollSync: scrollSync ?? this.scrollSync,
      debounceMs: debounceMs ?? this.debounceMs,
      llmDebounceMs: llmDebounceMs ?? this.llmDebounceMs,
      autoTargetLang: autoTargetLang ?? this.autoTargetLang,
      langFrom: langFrom ?? this.langFrom,
      langTo: langTo ?? this.langTo,
      llm: llm ?? this.llm.copyWith(),
      files: files ?? this.files.copyWith(),
      argos: argos ?? this.argos.copyWith(),
      behavior: behavior ?? this.behavior.copyWith(),
      activeTranslationTab: activeTranslationTab ?? this.activeTranslationTab,
      firstRunDone: firstRunDone ?? this.firstRunDone,
      defaultEngine: defaultEngine ?? this.defaultEngine,
      uiExtras: Map<String, Object?>.from(uiExtras ?? this.uiExtras),
      extras: Map<String, Object?>.from(extras ?? this.extras),
    );
  }

  Map<String, Object?> toJson() => mergeExtras(extras, {
        'version': version,
        'window': mergeExtras(window.extras, {
          'state': window.state,
          'x': window.x,
          'y': window.y,
          'width': window.width,
          'height': window.height,
          'dpi_scale': window.dpiScale,
          'geometry_units': window.geometryUnits,
          'opacity': window.opacity,
          'theme': window.theme,
          'font_scale': window.fontScale,
          'editor_layout': window.editorLayout,
          'editor_font': window.editorFont,
          'geometry_legacy': window.geometryLegacy,
        }),
        'translation': {
          'default_engine': defaultEngine,
          'streaming': streaming,
          'debounce_ms': debounceMs,
          'llm_debounce_ms': llmDebounceMs,
          'scroll_sync': scrollSync,
          'auto_target_lang': autoTargetLang,
          'cache_enabled': behavior.translationCacheEnabled,
          'cache_size': behavior.translationCacheSize,
        },
        'languages': {'from': langFrom, 'to': langTo},
        'llm': {
          'enabled': llm.enabled,
          'provider': llm.provider,
          'base_url': llm.baseUrl,
          'provider_urls': llm.providerUrls,
          'api_keys': llm.apiKeys,
          'api_key_refs': llm.apiKeyRefs,
          'model': llm.model,
          'auth_header': llm.authHeader,
          'temperature': llm.temperature,
          'max_tokens': llm.maxTokens,
          'timeout_sec': llm.timeoutSec,
          'stream': llm.stream,
          'health_check_ttl_sec': llm.healthCheckTtlSec,
          'system_prompt': llm.systemPrompt,
          'chunk_max_chars': llm.chunkMaxChars,
          'file_chunk_max_chars': llm.fileChunkMaxChars,
          'file_chunk_context': llm.fileChunkContext,
        },
        'ui': mergeExtras(uiExtras, {
          'active_translation_tab': activeTranslationTab,
          'first_run_done': firstRunDone,
        }),
        'files': {
          'output_encoding': files.outputEncoding,
          'output_suffix': files.outputSuffix,
          'max_file_size_mb': files.maxFileSizeMb,
          'hotkey_auto_translate_max_chars': files.hotkeyAutoTranslateMaxChars,
          'large_file_warn_chars': files.largeFileWarnChars,
          'translate_code_blocks': files.translateCodeBlocks,
        },
        'argos': {
          'packages_dir': argos.packagesDir,
          'prefer_api_over_cli': argos.preferApiOverCli,
          'bundle_models_on_start': argos.bundleModelsOnStart,
        },
        'behavior': {
          'close_action': behavior.closeAction,
          'start_minimized_to_tray': behavior.startMinimizedToTray,
          'tray_click_action': behavior.trayClickAction,
          'restore_clipboard_after_capture':
              behavior.restoreClipboardAfterCapture,
          'global_hotkey': behavior.globalHotkey,
          'minimize_to_tray_on_copy_hide': behavior.minimizeToTrayOnCopyHide,
          'triple_copy_enabled': behavior.tripleCopyEnabled,
        },
      });

  factory AppSettings.fromJson(Map<String, dynamic> json) {
    final data = migrateSettings(json);
    final window = asStringKeyedMap(data['window']);
    final translation = asStringKeyedMap(data['translation']);
    final languages = asStringKeyedMap(data['languages']);
    final llmData = asStringKeyedMap(data['llm']);
    final ui = asStringKeyedMap(data['ui']);
    final filesData = asStringKeyedMap(data['files']);
    final argosData = asStringKeyedMap(data['argos']);
    final behaviorData = asStringKeyedMap(data['behavior']);

    final cacheEnabled = readBool(
      translation['cache_enabled'] ?? behaviorData['translation_cache_enabled'],
      false,
    );
    final cacheSize = readInt(
      translation['cache_size'] ?? behaviorData['translation_cache_size'],
      500,
    );

    final providerUrls = readStringMap(llmData['provider_urls'], const {
      'local': '',
      'openrouter': 'https://openrouter.ai/api/v1',
      'custom': '',
    });
    final apiKeys = _migrateApiKeys(llmData);
    final apiKeyRefs = readStringMap(llmData['api_key_refs'], const {
      'openrouter': '',
      'custom': '',
    });

    return AppSettings(
      version: readInt(data['version'], currentSettingsVersion),
      window: WindowSettings(
        state: readString(window['state'], 'normal'),
        x: readInt(window['x'], 100),
        y: readInt(window['y'], 100),
        width: readInt(window['width'], 1000),
        height: readInt(window['height'], 700),
        dpiScale: readDouble(window['dpi_scale'], 1.0),
        geometryUnits: readString(window['geometry_units'], 'legacy'),
        opacity: readDouble(window['opacity'], 1.0),
        theme: readString(window['theme'], 'dark'),
        fontScale: readDouble(window['font_scale'], 1.0),
        editorLayout: readString(window['editor_layout'], 'split'),
        editorFont: readString(window['editor_font'], 'system'),
        geometryLegacy: window['geometry'] is String
            ? window['geometry'] as String
            : (window['geometry_legacy'] is String
                ? window['geometry_legacy'] as String
                : null),
        extras: leftoverFields(window, _windowKnownKeys),
      ),
      streaming: readBool(
        translation['streaming'] ?? window['streaming'],
        true,
      ),
      scrollSync: readBool(
        translation['scroll_sync'] ?? window['scroll_sync'],
        true,
      ),
      debounceMs: readInt(translation['debounce_ms'], 700),
      llmDebounceMs: readInt(translation['llm_debounce_ms'], 1200),
      autoTargetLang: readString(translation['auto_target_lang'], 'ru'),
      langFrom: readString(languages['from'], 'auto'),
      langTo: readString(languages['to'], 'ru'),
      llm: LlmSettings(
        enabled: readBool(llmData['enabled'], true),
        provider: readString(llmData['provider'], 'local'),
        baseUrl: readString(llmData['base_url'], ''),
        providerUrls: providerUrls,
        apiKeys: apiKeys,
        apiKeyRefs: apiKeyRefs,
        model: readString(llmData['model'], ''),
        authHeader: readString(llmData['auth_header'], 'auto'),
        temperature: readDouble(llmData['temperature'], 0.3),
        maxTokens: readInt(llmData['max_tokens'], 4096),
        timeoutSec: readInt(llmData['timeout_sec'], 120),
        stream: readBool(llmData['stream'], true),
        healthCheckTtlSec: readInt(llmData['health_check_ttl_sec'], 30),
        systemPrompt: readString(llmData['system_prompt'], ''),
        chunkMaxChars: readInt(llmData['chunk_max_chars'], 6000),
        fileChunkMaxChars: readInt(llmData['file_chunk_max_chars'], 3500),
        fileChunkContext: readBool(llmData['file_chunk_context'], true),
      ),
      files: FileSettings(
        outputEncoding: readString(filesData['output_encoding'], 'same'),
        outputSuffix: readString(filesData['output_suffix'], '_translated'),
        maxFileSizeMb: readInt(filesData['max_file_size_mb'], 10),
        hotkeyAutoTranslateMaxChars:
            readInt(filesData['hotkey_auto_translate_max_chars'], 500),
        largeFileWarnChars: readInt(filesData['large_file_warn_chars'], 50000),
        translateCodeBlocks:
            readBool(filesData['translate_code_blocks'], false),
      ),
      argos: ArgosEngineSettings(
        packagesDir: readString(argosData['packages_dir'], ''),
        preferApiOverCli: readBool(argosData['prefer_api_over_cli'], true),
        bundleModelsOnStart:
            readBool(argosData['bundle_models_on_start'], true),
      ),
      behavior: BehaviorSettings(
        closeAction: readString(behaviorData['close_action'], 'tray'),
        startMinimizedToTray:
            readBool(behaviorData['start_minimized_to_tray'], false),
        trayClickAction: readString(behaviorData['tray_click_action'], 'show'),
        restoreClipboardAfterCapture:
            readBool(behaviorData['restore_clipboard_after_capture'], true),
        globalHotkey: readString(behaviorData['global_hotkey'], ''),
        minimizeToTrayOnCopyHide:
            readBool(behaviorData['minimize_to_tray_on_copy_hide'], true),
        translationCacheEnabled: cacheEnabled,
        translationCacheSize: cacheSize,
        tripleCopyEnabled: readBool(behaviorData['triple_copy_enabled'], true),
      ),
      activeTranslationTab: readString(ui['active_translation_tab'], 'argos'),
      firstRunDone: readBool(ui['first_run_done'], false),
      defaultEngine: readString(translation['default_engine'], 'both_adaptive'),
      uiExtras: leftoverFields(ui, _uiKnownKeys),
      extras: leftoverFields(data, _topLevelKnownKeys),
    );
  }
}

const _topLevelKnownKeys = {
  'version',
  'window',
  'translation',
  'languages',
  'llm',
  'ui',
  'files',
  'argos',
  'behavior',
};

const _windowKnownKeys = {
  'state',
  'x',
  'y',
  'width',
  'height',
  'dpi_scale',
  'geometry_units',
  'opacity',
  'theme',
  'font_scale',
  'editor_layout',
  'editor_font',
  'geometry_legacy',
  'geometry',
  'streaming',
  'scroll_sync',
};

const _uiKnownKeys = {
  'active_translation_tab',
  'first_run_done',
};

Map<String, String> _migrateApiKeys(Map<String, dynamic> llmData) {
  final keys = llmData['api_keys'];
  if (keys is Map) {
    return keys.map(
      (key, dynamic v) => MapEntry(key.toString(), v?.toString() ?? ''),
    );
  }
  final result = <String, String>{'openrouter': '', 'custom': ''};
  final legacy = llmData['api_key'];
  if (legacy is String && legacy.isNotEmpty) {
    result['openrouter'] = legacy;
  }
  return result;
}

/// Миграция JSON настроек до v9. URL и ключи не стираются.
Map<String, dynamic> migrateSettings(Map<String, dynamic> input) {
  final data = Map<String, dynamic>.from(input);
  var version = readInt(data['version'], 1);

  if (version < 2) {
    final window = asStringKeyedMap(data['window']);
    final translation = asStringKeyedMap(data['translation']);
    if (window.containsKey('streaming') && !data.containsKey('translation')) {
      translation['streaming'] = window.remove('streaming');
    }
    if (window.containsKey('scroll_sync')) {
      translation['scroll_sync'] = window['scroll_sync'];
    }
    data['window'] = window;
    data['translation'] = translation;
    version = 2;
  }
  if (version < 3) {
    final translation = asStringKeyedMap(data['translation']);
    translation['default_engine'] = 'both_adaptive';
    data['translation'] = translation;
    version = 3;
  }
  if (version < 4) {
    final llm = asStringKeyedMap(data['llm']);
    if (llm.containsKey('api_key') && !llm.containsKey('api_keys')) {
      llm['api_keys'] = _migrateApiKeys(llm);
    }
    llm.putIfAbsent('provider', () => 'local');
    llm.putIfAbsent('enabled', () => true);
    data['llm'] = llm;
    version = 4;
  }
  if (version < 5) {
    final files = asStringKeyedMap(data['files']);
    files.putIfAbsent('output_encoding', () => 'same');
    files.putIfAbsent('output_suffix', () => '_translated');
    files.putIfAbsent('max_file_size_mb', () => 10);
    files.putIfAbsent('hotkey_auto_translate_max_chars', () => 500);
    files.putIfAbsent('large_file_warn_chars', () => 50000);
    files.putIfAbsent('translate_code_blocks', () => false);
    data['files'] = files;
    version = 5;
  }
  if (version < 6) {
    final argos = asStringKeyedMap(data['argos']);
    argos.putIfAbsent('packages_dir', () => '');
    argos.putIfAbsent('prefer_api_over_cli', () => true);
    argos.putIfAbsent('bundle_models_on_start', () => true);
    data['argos'] = argos;
    version = 6;
  }
  if (version < 7) {
    final behavior = asStringKeyedMap(data['behavior']);
    behavior.putIfAbsent('close_action', () => 'tray');
    behavior.putIfAbsent('start_minimized_to_tray', () => false);
    behavior.putIfAbsent('restore_clipboard_after_capture', () => true);
    behavior.putIfAbsent('minimize_to_tray_on_copy_hide', () => true);
    data['behavior'] = behavior;
    final translation = asStringKeyedMap(data['translation']);
    translation['cache_enabled'] = false;
    translation['cache_size'] = 500;
    data['translation'] = translation;
    version = 7;
  }
  if (version < 8) {
    final llm = asStringKeyedMap(data['llm']);
    llm.putIfAbsent('chunk_max_chars', () => 6000);
    llm.putIfAbsent('file_chunk_max_chars', () => 3500);
    llm.putIfAbsent('file_chunk_context', () => true);
    data['llm'] = llm;
    version = 8;
  }
  if (version < 9) {
    final ui = asStringKeyedMap(data['ui']);
    // Существующий файл — не показывать first-run.
    ui['first_run_done'] = true;
    data['ui'] = ui;
    final window = asStringKeyedMap(data['window']);
    window.putIfAbsent('editor_font', () => 'system');
    data['window'] = window;
    final llm = asStringKeyedMap(data['llm']);
    llm.putIfAbsent(
        'api_key_refs',
        () => <String, String>{
              'openrouter': '',
              'custom': '',
            });
    data['llm'] = llm;
    version = 9;
  }

  data['version'] = version;
  return data;
}
