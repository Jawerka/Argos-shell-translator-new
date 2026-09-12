import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:translator_core/translator_core.dart';

import 'core/app_log.dart';
import 'platform/llm_key_store.dart';

bool inFlutterTest() {
  if (kIsWeb) {
    return false;
  }
  return Platform.environment.containsKey('FLUTTER_TEST');
}

class SettingsController extends Notifier<AppSettings> {
  SettingsController([this.initial]);

  final AppSettings? initial;
  final store = SettingsStore();

  @override
  AppSettings build() => initial ?? const AppSettings();

  /// Только state, без записи JSON (живой preview темы до «Применить»).
  void replaceLocal(AppSettings next) {
    state = next;
  }

  Future<void> update(AppSettings next) async {
    state = next;
    if (inFlutterTest()) {
      return;
    }
    try {
      await store.save(next);
    } catch (e, st) {
      AppLog.warning('settings save failed', e, st);
    }
  }

  /// Повторная загрузка с диска и перенос ключей (если UI грузит настройки позже).
  Future<void> loadAndMigrateSecrets(LlmKeyStore keyStore) async {
    final loaded = await store.load();
    state = await persistMigratedLlmSecrets(
      settings: loaded,
      keyStore: keyStore,
      store: store,
    );
  }
}

final settingsProvider =
    NotifierProvider<SettingsController, AppSettings>(SettingsController.new);

final sidecarClientProvider = StateProvider<SidecarClient?>((_) => null);

final llmClientProvider = Provider<LlmClient>((_) => LlmClient());

final llmKeyStoreProvider = Provider<LlmKeyStore>((_) => LlmKeyStore());
