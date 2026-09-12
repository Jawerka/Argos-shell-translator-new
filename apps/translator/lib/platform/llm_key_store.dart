import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:translator_core/translator_core.dart';

import '../core/app_log.dart';

bool _inFlutterTest() {
  if (kIsWeb) {
    return false;
  }
  return Platform.environment.containsKey('FLUTTER_TEST');
}

/// Ключи LLM: secure storage, в тестах и при сбое — память.
class LlmKeyStore {
  LlmKeyStore({
    FlutterSecureStorage? storage,
    Map<String, String>? memory,
    bool? usePlatformStorage,
  }) : _memory = Map<String, String>.from(memory ?? const {}) {
    final wantPlatform = usePlatformStorage ?? !_inFlutterTest();
    if (wantPlatform) {
      _storage = storage ?? const FlutterSecureStorage();
      _usePlatform = true;
    } else {
      _storage = storage;
      _usePlatform = storage != null;
    }
  }

  final Map<String, String> _memory;
  FlutterSecureStorage? _storage;
  var _usePlatform = false;

  String cached(String provider) => _memory[provider] ?? '';

  Future<String> read(String provider) async {
    final cachedValue = _memory[provider];
    if (cachedValue != null && cachedValue.isNotEmpty) {
      return cachedValue;
    }
    if (!_usePlatform || _storage == null) {
      return cachedValue ?? '';
    }
    try {
      final value =
          await _storage!.read(key: llmApiKeyStorageKey(provider)) ?? '';
      if (value.isNotEmpty) {
        _memory[provider] = value;
      }
      return value;
    } catch (e, st) {
      AppLog.warning('secure storage read failed', e, st);
      _usePlatform = false;
      return cachedValue ?? '';
    }
  }

  /// `true`, если ключ устойчиво записан (платформа или память-как-хранилище).
  Future<bool> write(String provider, String value) async {
    _memory[provider] = value;
    if (!_usePlatform || _storage == null) {
      return true;
    }
    try {
      final key = llmApiKeyStorageKey(provider);
      if (value.isEmpty) {
        await _storage!.delete(key: key);
      } else {
        await _storage!.write(key: key, value: value);
      }
      return true;
    } catch (e, st) {
      AppLog.warning('secure storage write failed', e, st);
      _usePlatform = false;
      return false;
    }
  }

  Future<void> preload() async {
    await read('openrouter');
    await read('custom');
  }

  Future<LlmSettings> attach(LlmSettings llm) async {
    final keys = Map<String, String>.from(llm.apiKeys);
    for (final provider in const ['openrouter', 'custom']) {
      if ((keys[provider] ?? '').trim().isNotEmpty) {
        continue;
      }
      final stored = await read(provider);
      if (stored.isNotEmpty) {
        keys[provider] = stored;
      }
    }
    return llm.copyWith(apiKeys: keys);
  }

  LlmSettings attachCached(LlmSettings llm) {
    final keys = Map<String, String>.from(llm.apiKeys);
    for (final provider in const ['openrouter', 'custom']) {
      if ((keys[provider] ?? '').trim().isNotEmpty) {
        continue;
      }
      final stored = cached(provider);
      if (stored.isNotEmpty) {
        keys[provider] = stored;
      }
    }
    return llm.copyWith(apiKeys: keys);
  }
}

/// После загрузки settings.json: plaintext → secure storage, в JSON — refs.
Future<AppSettings> persistMigratedLlmSecrets({
  required AppSettings settings,
  required LlmKeyStore keyStore,
  required SettingsStore store,
  bool persistToDisk = true,
}) async {
  final migrated = migratePlaintextLlmApiKeys(
    apiKeys: settings.llm.apiKeys,
    apiKeyRefs: settings.llm.apiKeyRefs,
  );

  var platformOk = true;
  if (migrated.didMigrate) {
    for (final entry in migrated.secretsToStore.entries) {
      final ok = await keyStore.write(entry.key, entry.value);
      if (!ok) {
        platformOk = false;
      }
    }
    AppLog.info('migrated llm api keys to secure storage');
  }

  await keyStore.preload();

  final stripped = settings.copyWith(
    llm: settings.llm.copyWith(
      apiKeys: migrated.apiKeys,
      apiKeyRefs: migrated.apiKeyRefs,
    ),
  );

  if (migrated.didMigrate && platformOk && persistToDisk && !_inFlutterTest()) {
    try {
      await store.save(stripped);
    } catch (e, st) {
      AppLog.warning('settings save after key migration failed', e, st);
    }
  } else if (migrated.didMigrate && !platformOk) {
    AppLog.warning(
      'secure storage unavailable, llm keys kept for this session',
    );
  }

  // В RAM ключи живут в LlmKeyStore; в state — пустые apiKeys.
  return stripped;
}

AppSettings settingsWithoutPlaintextKeys(
  AppSettings settings, {
  String? editedProvider,
}) {
  final strip = stripLlmApiKeysForPersist(
    settings.llm.apiKeys,
    settings.llm.apiKeyRefs,
    editedProvider: editedProvider,
  );
  return settings.copyWith(
    llm: settings.llm.copyWith(
      apiKeys: strip.apiKeys,
      apiKeyRefs: strip.apiKeyRefs,
    ),
  );
}
