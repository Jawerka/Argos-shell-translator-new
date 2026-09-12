import 'package:flutter_test/flutter_test.dart';
import 'package:translator/platform/llm_key_store.dart';
import 'package:translator_core/translator_core.dart';

void main() {
  test('LlmKeyStore memory backend stores keys without plugin', () async {
    final store = LlmKeyStore(usePlatformStorage: false);
    await store.write('openrouter', 'sk-test');
    expect(await store.read('openrouter'), 'sk-test');
    final attached = await store.attach(
      const LlmSettings(provider: 'openrouter'),
    );
    expect(attached.apiKeys['openrouter'], 'sk-test');
    expect(const AppSettings().llm.baseUrl, isEmpty);
  });

  test('persistMigratedLlmSecrets clears plaintext and sets refs', () async {
    const settings = AppSettings(
      llm: LlmSettings(
        apiKeys: {'openrouter': 'sk-secret', 'custom': ''},
        apiKeyRefs: {'openrouter': '', 'custom': ''},
      ),
    );
    final keys = LlmKeyStore(usePlatformStorage: false);
    final next = await persistMigratedLlmSecrets(
      settings: settings,
      keyStore: keys,
      store: SettingsStore(),
      persistToDisk: false,
    );
    expect(next.llm.apiKeys['openrouter'], isEmpty);
    expect(next.llm.apiKeyRefs['openrouter'], 'argos.llm.openrouter');
    expect(await keys.read('openrouter'), 'sk-secret');
    expect(next.toJson().toString().contains('sk-secret'), isFalse);
    expect(next.toJson().toString().contains('192.168.88.41'), isFalse);
  });
}
