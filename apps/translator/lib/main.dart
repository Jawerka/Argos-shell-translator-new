import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:translator_core/translator_core.dart';
import 'package:window_manager/window_manager.dart';

import 'app.dart';
import 'core/app_log.dart';
import 'platform/desktop_shell.dart';
import 'platform/instance_agent.dart';
import 'platform/llm_key_store.dart';
import 'platform/window_geometry.dart';
import 'platform/window_shell.dart';
import 'providers.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppLog.setup();

  if (!kIsWeb && Platform.isWindows && !inWidgetTest) {
    await startInstanceAgentOrHandoff();
  }

  final loaded = await SettingsStore().load();
  AppLog.info('settings version=${loaded.version} theme=${loaded.theme}');

  final keyStore = LlmKeyStore();
  final settings = await persistMigratedLlmSecrets(
    settings: loaded,
    keyStore: keyStore,
    store: SettingsStore(),
  );

  if (!kIsWeb && Platform.isWindows && !inWidgetTest) {
    await DesktopShell.instance.prepareWindowManager(
      minSize: const Size(800, 600),
      title: 'Argos Translate',
    );
    final geometry = (await WindowStateStore.load()).clampToVisible();
    await WindowShell.applyBounds(
      WindowStateStore.toRect(geometry),
      maximized: geometry.maximized,
    );
    await WindowShell.setOpacity(settings.window.opacity);
    await windowManager.setPreventClose(true);
  }

  runApp(
    ProviderScope(
      overrides: [
        settingsProvider.overrideWith(() => SettingsController(settings)),
        llmKeyStoreProvider.overrideWith((ref) => keyStore),
      ],
      child: const TranslatorApp(),
    ),
  );
}
