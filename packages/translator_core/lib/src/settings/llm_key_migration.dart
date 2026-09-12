import '../json_util.dart';

/// Имя ключа в secure storage / значение `api_key_refs`.
String llmApiKeyStorageKey(String provider) => 'argos.llm.$provider';

/// Результат переноса plaintext `api_keys` в refs (без записи на диск).
class LlmApiKeyMigrationResult {
  const LlmApiKeyMigrationResult({
    required this.apiKeys,
    required this.apiKeyRefs,
    required this.secretsToStore,
  });

  /// Пустые значения на месте бывших plaintext-ключей.
  final Map<String, String> apiKeys;

  /// Ссылки вида `argos.llm.openrouter`.
  final Map<String, String> apiKeyRefs;

  /// Провайдер → исходный ключ (только для записи в secure storage).
  final Map<String, String> secretsToStore;

  bool get didMigrate => secretsToStore.isNotEmpty;
}

/// Переносит непустые plaintext-ключи openrouter/custom в refs.
///
/// JSON после этого не содержит секретов; сами значения только в
/// [LlmApiKeyMigrationResult.secretsToStore] (не логировать).
LlmApiKeyMigrationResult migratePlaintextLlmApiKeys({
  required Map<String, String> apiKeys,
  Map<String, String> apiKeyRefs = const {},
}) {
  final nextKeys = <String, String>{
    for (final entry in apiKeys.entries) entry.key: '',
  };
  final nextRefs = Map<String, String>.from(apiKeyRefs);
  final secrets = <String, String>{};

  for (final entry in apiKeys.entries) {
    final provider = entry.key;
    if (provider == 'local') {
      continue;
    }
    final plaintext = entry.value.trim();
    if (plaintext.isEmpty) {
      continue;
    }
    secrets[provider] = plaintext;
    nextRefs[provider] = llmApiKeyStorageKey(provider);
    nextKeys[provider] = '';
  }

  return LlmApiKeyMigrationResult(
    apiKeys: nextKeys,
    apiKeyRefs: nextRefs,
    secretsToStore: secrets,
  );
}

/// То же для карты settings.json: пустые `api_keys` + заполненные `api_key_refs`.
class LlmApiKeyJsonMigration {
  const LlmApiKeyJsonMigration({
    required this.json,
    required this.secretsToStore,
  });

  final Map<String, dynamic> json;
  final Map<String, String> secretsToStore;
}

LlmApiKeyJsonMigration migratePlaintextApiKeysInSettingsJson(
  Map<String, dynamic> input,
) {
  final data = Map<String, dynamic>.from(input);
  final llm = asStringKeyedMap(data['llm']);
  final migrated = migratePlaintextLlmApiKeys(
    apiKeys: readStringMap(llm['api_keys'], const {
      'openrouter': '',
      'custom': '',
    }),
    apiKeyRefs: readStringMap(llm['api_key_refs'], const {
      'openrouter': '',
      'custom': '',
    }),
  );
  llm['api_keys'] = migrated.apiKeys;
  llm['api_key_refs'] = migrated.apiKeyRefs;
  data['llm'] = llm;
  return LlmApiKeyJsonMigration(
    json: data,
    secretsToStore: migrated.secretsToStore,
  );
}

/// Обнуляет `apiKeys` перед записью JSON; refs для непустых ключей.
LlmSettingsStrip stripLlmApiKeysForPersist(
  Map<String, String> apiKeys,
  Map<String, String> apiKeyRefs, {
  String? editedProvider,
}) {
  final keys = <String, String>{
    for (final entry in apiKeys.entries) entry.key: '',
  };
  final refs = Map<String, String>.from(apiKeyRefs);
  for (final entry in apiKeys.entries) {
    if (entry.key == 'local') {
      continue;
    }
    if (entry.value.trim().isNotEmpty) {
      refs[entry.key] = llmApiKeyStorageKey(entry.key);
    }
  }
  if (editedProvider != null &&
      editedProvider != 'local' &&
      (apiKeys[editedProvider] ?? '').trim().isEmpty) {
    refs[editedProvider] = '';
  }
  return LlmSettingsStrip(apiKeys: keys, apiKeyRefs: refs);
}

class LlmSettingsStrip {
  const LlmSettingsStrip({
    required this.apiKeys,
    required this.apiKeyRefs,
  });

  final Map<String, String> apiKeys;
  final Map<String, String> apiKeyRefs;
}
