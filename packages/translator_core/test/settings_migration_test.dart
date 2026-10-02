import 'dart:convert';
import 'dart:io';

import 'package:test/test.dart';
import 'package:translator_core/translator_core.dart';

void main() {
  test('v8 file migrates to v9 without stripping urls or keys', () {
    const lanUrl = 'http://192.168.88.41:8989/v1';
    final v8 = <String, dynamic>{
      'version': 8,
      'window': {
        'theme': 'light',
        'x': 40,
        'y': 50,
        'width': 1100,
        'height': 720,
      },
      'llm': {
        'enabled': true,
        'provider': 'local',
        'base_url': lanUrl,
        'provider_urls': {
          'local': lanUrl,
          'openrouter': 'https://openrouter.ai/api/v1',
          'custom': '',
        },
        'api_keys': {'openrouter': 'sk-keep-me', 'custom': 'abc'},
      },
      'behavior': {
        'global_hotkey': 'ctrl+shift+c',
      },
    };

    final migrated = migrateSettings(v8);
    expect(migrated['version'], 10);
    final ui = migrated['ui'] as Map<String, dynamic>;
    expect(ui['first_run_done'], isTrue);
    final llm = migrated['llm'] as Map<String, dynamic>;
    expect(llm['base_url'], lanUrl);
    expect((llm['provider_urls'] as Map)['local'], lanUrl);
    expect((llm['api_keys'] as Map)['openrouter'], 'sk-keep-me');
    expect(llm['api_key_refs'], isA<Map<dynamic, dynamic>>());

    final settings = AppSettings.fromJson(v8);
    expect(settings.version, 10);
    expect(settings.firstRunDone, isTrue);
    expect(settings.llm.baseUrl, lanUrl);
    expect(settings.llm.providerUrls['local'], lanUrl);
    expect(settings.llm.apiKeys['openrouter'], 'sk-keep-me');
    expect(settings.window.theme, 'light');
    expect(settings.window.editorFont, 'system');
    expect(settings.behavior.globalHotkey, 'ctrl+shift+c');
  });

  test('v8 without hotkey key does not invent a shortcut', () {
    final settings = AppSettings.fromJson({'version': 8});
    expect(settings.firstRunDone, isTrue);
    expect(settings.behavior.globalHotkey, isEmpty);
    expect(settings.llm.baseUrl, isEmpty);
  });

  test('new settings default to empty local URL and first_run_done false', () {
    const settings = AppSettings();
    expect(settings.version, 10);
    expect(settings.firstRunDone, isFalse);
    expect(settings.llm.baseUrl, isEmpty);
    expect(settings.llm.providerUrls['local'], isEmpty);
    expect(settings.behavior.globalHotkey, isEmpty);
    expect(settings.llm.baseUrl.contains('192.168'), isFalse);

    final json = settings.toJson();
    expect(json['version'], 10);
    expect((json['ui'] as Map)['first_run_done'], isFalse);
    expect((json['llm'] as Map)['base_url'], isEmpty);
    expect(json.toString().contains('192.168.88.41'), isFalse);
  });

  test('load missing file returns new defaults; save round-trips v9', () async {
    final dir = await Directory.systemTemp.createTemp('argos_settings_');
    addTearDown(() => dir.delete(recursive: true));
    final store = SettingsStore(configDir: dir);

    final loaded = await store.load();
    expect(loaded.firstRunDone, isFalse);
    expect(loaded.llm.baseUrl, isEmpty);

    await store.save(loaded);
    final text = await store.file.readAsString();
    final decoded = jsonDecode(text) as Map<String, dynamic>;
    expect(decoded['version'], 10);
    expect((decoded['ui'] as Map)['first_run_done'], isFalse);

    final again = await store.load();
    expect(again.version, 10);
    expect(again.llm.apiKeyRefs.containsKey('openrouter'), isTrue);
  });

  test('load corrupt JSON returns defaults', () async {
    final dir = await Directory.systemTemp.createTemp('argos_settings_');
    addTearDown(() => dir.delete(recursive: true));
    final store = SettingsStore(configDir: dir);
    await store.file.writeAsString('{not json');
    final loaded = await store.load();
    expect(loaded.debounceMs, 700);
    expect(loaded.window.opacity, 1.0);
  });

  test('load clamps negative numbers and invalid enums', () async {
    final dir = await Directory.systemTemp.createTemp('argos_settings_');
    addTearDown(() => dir.delete(recursive: true));
    final store = SettingsStore(configDir: dir);
    await store.file.writeAsString(
      jsonEncode({
        'version': 9,
        'translation': {'debounce_ms': -999, 'cache_size': 1},
        'window': {
          'opacity': 0.01,
          'font_scale': 0.2,
          'theme': 'neon',
          'editor_font': 'comic',
        },
        'files': {
          'output_encoding': 'cp1251',
          'max_file_size_mb': 0,
          'hotkey_auto_translate_max_chars': 1,
        },
        'llm': {
          'provider': 'foo',
          'temperature': 9,
          'auth_header': 'nope',
        },
        'behavior': {'close_action': 'explode'},
      }),
    );
    final loaded = await store.load();
    expect(loaded.debounceMs, 100);
    expect(loaded.behavior.translationCacheSize, 10);
    expect(loaded.window.opacity, 0.3);
    expect(loaded.window.fontScale, 1.0);
    expect(loaded.window.theme, 'dark');
    expect(loaded.window.editorFont, 'system');
    expect(loaded.files.outputEncoding, 'same');
    expect(loaded.files.maxFileSizeMb, 1);
    expect(loaded.files.hotkeyAutoTranslateMaxChars, 50);
    expect(loaded.llm.provider, 'local');
    expect(loaded.llm.temperature, 2.0);
    expect(loaded.llm.authHeader, 'auto');
    expect(loaded.behavior.closeAction, 'tray');
  });

  test('unknown CTk fields round-trip via extras', () {
    final settings = AppSettings.fromJson({
      'version': 9,
      'window': {
        'theme': 'dark',
        'monitor_hint': {'device': 'Dell', 'index': 1},
      },
      'ui': {
        'first_run_done': true,
        'settings_dialog': {'width': 720, 'height': 560},
      },
      'custom_top': {'keep': true},
    });
    expect(settings.window.extras['monitor_hint'], isA<Map<Object?, Object?>>());
    expect((settings.uiExtras['settings_dialog'] as Map<Object?, Object?>)['width'], 720);
    expect(settings.extras['custom_top'], isA<Map<Object?, Object?>>());

    final json = settings.toJson();
    final window = json['window'] as Map<Object?, Object?>;
    expect(window['monitor_hint'], isA<Map<Object?, Object?>>());
    final ui = json['ui'] as Map<Object?, Object?>;
    expect((ui['settings_dialog'] as Map<Object?, Object?>)['width'], 720);
    expect(json['custom_top'], isA<Map<Object?, Object?>>());
  });

  test('v9 en/ru pair becomes AUTO ru and leaves other pairs', () {
    const prompt = 'Переведи текст. Только перевод.';
    final v9 = <String, dynamic>{
      'version': 9,
      'window': {
        'state': 'normal',
        'x': 245,
        'y': 201,
        'width': 800,
        'height': 600,
        'opacity': 1.0,
        'theme': 'dark',
        'font_scale': 1.4,
        'editor_layout': 'split',
        'editor_font': 'system',
      },
      'translation': {
        'streaming': true,
        'debounce_ms': 700,
        'llm_debounce_ms': 1200,
        'auto_target_lang': 'en',
      },
      'languages': {'from': 'en', 'to': 'ru'},
      'llm': {
        'enabled': true,
        'provider': 'local',
        'base_url': 'http://127.0.0.1:8989/v1',
        'provider_urls': {
          'local': 'http://127.0.0.1:8989/v1',
          'openrouter': 'https://openrouter.ai/api/v1',
          'custom': '',
        },
        'model': 'local-model',
        'system_prompt': prompt,
      },
      'ui': {'active_translation_tab': 'llm', 'first_run_done': true},
      'behavior': {'global_hotkey': 'ctrl+shift+c', 'triple_copy_enabled': true},
    };

    final settings = AppSettings.fromJson(v9);
    expect(settings.version, 10);
    expect(settings.langFrom, 'auto');
    expect(settings.langTo, 'ru');
    expect(settings.autoTargetLang, 'ru');
    expect(settings.llm.baseUrl, 'http://127.0.0.1:8989/v1');
    expect(settings.llm.systemPrompt, prompt);
    expect(settings.llm.providerUrls['local'], 'http://127.0.0.1:8989/v1');
    expect(settings.window.fontScale, closeTo(1.4, 0.001));
    expect(settings.activeTranslationTab, 'llm');

    final other = AppSettings.fromJson({
      'version': 9,
      'languages': {'from': 'de', 'to': 'fr'},
      'translation': {'auto_target_lang': 'fr'},
    });
    expect(other.version, 10);
    expect(other.langFrom, 'de');
    expect(other.langTo, 'fr');
    expect(other.autoTargetLang, 'fr');
  });

  test('clamp health_check_ttl_sec', () {
    final low = clampAppSettings(
      const AppSettings(llm: LlmSettings(healthCheckTtlSec: 1)),
    );
    expect(low.llm.healthCheckTtlSec, 5);
    final high = clampAppSettings(
      const AppSettings(llm: LlmSettings(healthCheckTtlSec: 9999)),
    );
    expect(high.llm.healthCheckTtlSec, 300);
  });
}
