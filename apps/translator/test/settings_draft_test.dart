import 'package:flutter_test/flutter_test.dart';
import 'package:translator/features/settings/settings_draft.dart';
import 'package:translator_core/translator_core.dart';

void main() {
  test('clampArgosDebounceMs stays in 100–5000', () {
    expect(clampArgosDebounceMs(50), 100);
    expect(clampArgosDebounceMs(700), 700);
    expect(clampArgosDebounceMs(9000), 5000);
  });

  test('clampLlmDebounceMs stays in 200–10000', () {
    expect(clampLlmDebounceMs(10), 200);
    expect(clampLlmDebounceMs(1200), 1200);
    expect(clampLlmDebounceMs(20000), 10000);
  });

  test('clampAppSettings clamps nested numeric fields', () {
    final clamped = clampAppSettings(
      const AppSettings(
        debounceMs: 1,
        llmDebounceMs: 1,
        window: WindowSettings(fontScale: 0.2, opacity: 0.05),
        behavior: BehaviorSettings(translationCacheSize: 1),
      ),
    );
    expect(clamped.debounceMs, 100);
    expect(clamped.llmDebounceMs, 200);
    expect(clamped.window.fontScale, 1.0);
    expect(clamped.window.opacity, 0.3);
    expect(clamped.behavior.translationCacheSize, 10);
  });

  test('clampAppSettings normalizes enums, temperature, chunks and files', () {
    final clamped = clampAppSettings(
      const AppSettings(
        window: WindowSettings(theme: 'neon', editorFont: 'comic'),
        llm: LlmSettings(
          provider: 'unknown',
          authHeader: 'nope',
          temperature: 9,
          maxTokens: 1,
          timeoutSec: 1,
          chunkMaxChars: 10,
          fileChunkMaxChars: 10,
        ),
        files: FileSettings(
          outputEncoding: 'cp1251',
          outputSuffix: '   ',
          maxFileSizeMb: 0,
          largeFileWarnChars: 10,
          hotkeyAutoTranslateMaxChars: 1,
        ),
        behavior: BehaviorSettings(closeAction: 'explode'),
      ),
    );
    expect(clamped.window.theme, 'dark');
    expect(clamped.window.editorFont, 'system');
    expect(clamped.llm.provider, 'local');
    expect(clamped.llm.authHeader, 'auto');
    expect(clamped.llm.temperature, 2.0);
    expect(clamped.llm.maxTokens, 64);
    expect(clamped.llm.timeoutSec, 5);
    expect(clamped.llm.chunkMaxChars, 500);
    expect(clamped.llm.fileChunkMaxChars, 500);
    expect(clamped.files.outputEncoding, 'same');
    expect(clamped.files.outputSuffix, '_translated');
    expect(clamped.files.maxFileSizeMb, 1);
    expect(clamped.files.largeFileWarnChars, 1000);
    expect(clamped.files.hotkeyAutoTranslateMaxChars, 50);
    expect(clamped.behavior.closeAction, 'tray');
  });

  test('parseIntField falls back on garbage', () {
    expect(parseIntField('50', 700), 50);
    expect(parseIntField('x', 700), 700);
  });
}
