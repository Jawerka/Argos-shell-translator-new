import 'app_settings.dart';

int clampArgosDebounceMs(int value) => value.clamp(100, 5000);

int clampLlmDebounceMs(int value) => value.clamp(200, 10000);

double clampFontScale(double value) => value.clamp(1.0, 2.0);

double clampOpacity(double value) => value.clamp(0.3, 1.0);

/// Ограничить числовые и enum-поля перед записью и после загрузки JSON.
AppSettings clampAppSettings(AppSettings settings) {
  final theme = settings.window.theme == 'light' ? 'light' : 'dark';
  final editorFont = settings.window.editorFont == 'mono' ? 'mono' : 'system';
  final encoding = switch (settings.files.outputEncoding) {
    'utf-8' => 'utf-8',
    'utf-8-sig' => 'utf-8-sig',
    _ => 'same',
  };
  final closeAction = settings.behavior.closeAction == 'exit' ? 'exit' : 'tray';
  final provider = switch (settings.llm.provider) {
    'openrouter' => 'openrouter',
    'custom' => 'custom',
    _ => 'local',
  };
  final authHeader = switch (settings.llm.authHeader) {
    'Bearer' => 'Bearer',
    'api-key' => 'api-key',
    _ => 'auto',
  };
  final suffix = settings.files.outputSuffix.trim().isEmpty
      ? '_translated'
      : settings.files.outputSuffix.trim();

  return settings.copyWith(
    debounceMs: clampArgosDebounceMs(settings.debounceMs),
    llmDebounceMs: clampLlmDebounceMs(settings.llmDebounceMs),
    window: settings.window.copyWith(
      theme: theme,
      editorFont: editorFont,
      fontScale: clampFontScale(settings.window.fontScale).toDouble(),
      opacity: clampOpacity(settings.window.opacity).toDouble(),
    ),
    llm: settings.llm.copyWith(
      provider: provider,
      authHeader: authHeader,
      temperature: settings.llm.temperature.clamp(0.0, 2.0).toDouble(),
      maxTokens: settings.llm.maxTokens.clamp(64, 128000),
      timeoutSec: settings.llm.timeoutSec.clamp(5, 600),
      healthCheckTtlSec: settings.llm.healthCheckTtlSec.clamp(5, 300),
      chunkMaxChars:
          settings.llm.chunkMaxChars < 500 ? 500 : settings.llm.chunkMaxChars,
      fileChunkMaxChars: settings.llm.fileChunkMaxChars < 500
          ? 500
          : settings.llm.fileChunkMaxChars,
    ),
    files: settings.files.copyWith(
      outputEncoding: encoding,
      outputSuffix: suffix,
      maxFileSizeMb: settings.files.maxFileSizeMb.clamp(1, 500),
      largeFileWarnChars: settings.files.largeFileWarnChars < 1000
          ? 1000
          : settings.files.largeFileWarnChars,
      hotkeyAutoTranslateMaxChars:
          settings.files.hotkeyAutoTranslateMaxChars < 50
              ? 50
              : settings.files.hotkeyAutoTranslateMaxChars,
    ),
    behavior: settings.behavior.copyWith(
      closeAction: closeAction,
      translationCacheSize:
          settings.behavior.translationCacheSize.clamp(10, 10000),
    ),
  );
}
