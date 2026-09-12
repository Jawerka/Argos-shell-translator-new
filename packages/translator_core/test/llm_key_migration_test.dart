import 'dart:convert';

import 'package:test/test.dart';
import 'package:translator_core/translator_core.dart';

void main() {
  test('v9 json plaintext api keys become empty api_keys plus refs', () {
    final v9 = <String, dynamic>{
      'version': 9,
      'llm': {
        'enabled': true,
        'provider': 'openrouter',
        'base_url': '',
        'api_keys': {'openrouter': 'sk-keep-me', 'custom': 'abc'},
        'api_key_refs': {'openrouter': '', 'custom': ''},
      },
    };

    final result = migratePlaintextApiKeysInSettingsJson(v9);
    final llm = result.json['llm'] as Map<String, dynamic>;
    final keys = Map<String, String>.from(llm['api_keys'] as Map);
    final refs = Map<String, String>.from(llm['api_key_refs'] as Map);

    expect(keys['openrouter'], isEmpty);
    expect(keys['custom'], isEmpty);
    expect(refs['openrouter'], 'argos.llm.openrouter');
    expect(refs['custom'], 'argos.llm.custom');
    expect(result.secretsToStore['openrouter'], 'sk-keep-me');
    expect(result.secretsToStore['custom'], 'abc');
    expect(jsonEncode(result.json).contains('sk-keep-me'), isFalse);
    expect(jsonEncode(result.json).contains('192.168.88.41'), isFalse);
  });

  test('empty api keys do not invent refs or secrets', () {
    final result = migratePlaintextLlmApiKeys(
      apiKeys: const {'openrouter': '', 'custom': ''},
      apiKeyRefs: const {'openrouter': '', 'custom': ''},
    );
    expect(result.didMigrate, isFalse);
    expect(result.secretsToStore, isEmpty);
    expect(result.apiKeyRefs['openrouter'], isEmpty);
    expect(result.apiKeys['openrouter'], isEmpty);
  });

  test('new AppSettings json has empty local URL and no LAN IP', () {
    const settings = AppSettings();
    expect(settings.llm.baseUrl, isEmpty);
    expect(settings.toJson().toString().contains('192.168.88.41'), isFalse);
  });
}
