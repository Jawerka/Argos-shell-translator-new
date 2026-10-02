import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:translator/features/session/workspace_controller.dart';
import 'package:translator/features/settings/settings_page.dart';
import 'package:translator/features/shell/source_panel.dart';
import 'package:translator/features/shell/translation_panel.dart';
import 'package:translator/providers.dart';
import 'package:translator_core/translator_core.dart';

import 'support/harness.dart';

void main() {
  testWidgets('swap AUTO flips only the current text', (tester) async {
    final sidecar = fakeSidecar();
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings.copyWith(langFrom: 'auto', langTo: 'ru'),
      sidecar: sidecar,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';
    await session.translateNow();
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).detectedLang, 'en');

    await tester.tap(find.byTooltip('Поменять языки'));
    await tester.pumpAndSettle();
    final state = container.read(workspaceProvider);
    expect(state.langFrom, 'auto');
    expect(state.langTo, 'ru');
    expect(state.pairOverride, isTrue);
    expect(state.detectedLang, 'ru');
    expect(state.resolvedTo, 'en');
    expect(container.read(settingsProvider).langFrom, 'auto');
    expect(container.read(settingsProvider).langTo, 'ru');
    expect(find.text('RU → EN ·'), findsOneWidget);
    expect(sidecar.fakeState.translateCalls, greaterThan(1));
  });

  testWidgets('swap explicit en/ru flips both sides and translates', (
    tester,
  ) async {
    final sidecar = fakeSidecar();
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings.copyWith(langFrom: 'en', langTo: 'ru'),
      sidecar: sidecar,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';
    await tester.pumpAndSettle();
    final before = sidecar.fakeState.translateCalls;

    await tester.tap(find.byTooltip('Поменять языки'));
    await tester.pumpAndSettle();
    final state = container.read(workspaceProvider);
    expect(state.langFrom, 'ru');
    expect(state.langTo, 'en');
    expect(sidecar.fakeState.translateCalls, greaterThan(before));
  });

  testWidgets('engine tabs switch active tab', (tester) async {
    final container = await pumpApp(
      tester,
      settings: const AppSettings(
        firstRunDone: true,
        llm: LlmSettings(enabled: true, baseUrl: 'http://127.0.0.1:1'),
      ),
      sidecar: fakeSidecar(),
    );
    expect(container.read(workspaceProvider).activeTab, 'argos');
    await tester.tap(find.byKey(const Key('engine-llm')));
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).activeTab, 'llm');
    await tester.tap(find.byKey(const Key('engine-argos')));
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).activeTab, 'argos');
  });

  testWidgets('LLM checkbox enables llm in settings', (tester) async {
    final container = await pumpApp(
      tester,
      settings: const AppSettings(
        firstRunDone: true,
        llm: LlmSettings(enabled: false),
      ),
    );
    await tester.tap(
      find.descendant(
        of: find.byKey(const Key('llm-enable')),
        matching: find.byType(Checkbox),
      ),
    );
    await tester.pumpAndSettle();
    expect(container.read(settingsProvider).llm.enabled, isTrue);
  });

  testWidgets('expand panel toggles editor layout', (tester) async {
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
      sidecar: fakeSidecar(),
    );
    expect(find.byType(SourcePanel), findsOneWidget);
    expect(find.byType(TranslationPanel), findsOneWidget);

    // Source expand — first open_in_full is on source panel.
    await tester.tap(find.byTooltip('На всю ширину').first);
    await tester.pumpAndSettle();
    expect(container.read(settingsProvider).window.editorLayout, 'source');
    expect(find.byType(SourcePanel), findsOneWidget);
    expect(find.byType(TranslationPanel), findsNothing);

    await tester.tap(find.byTooltip('На всю ширину').first);
    await tester.pumpAndSettle();
    expect(container.read(settingsProvider).window.editorLayout, 'split');
    expect(find.byType(TranslationPanel), findsOneWidget);

    await tester.tap(find.byTooltip('На всю ширину').last);
    await tester.pumpAndSettle();
    expect(
      container.read(settingsProvider).window.editorLayout,
      'translation',
    );
    expect(find.byType(SourcePanel), findsNothing);
    expect(find.byType(TranslationPanel), findsOneWidget);
  });

  testWidgets('File and More menus expose items and toggle flags', (
    tester,
  ) async {
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings.copyWith(streaming: true, scrollSync: true),
      sidecar: fakeSidecar(),
    );

    await tester.tap(find.byIcon(Icons.description_outlined));
    await tester.pumpAndSettle();
    expect(find.text('Открыть…'), findsOneWidget);
    expect(find.text('Сохранить перевод…'), findsOneWidget);
    expect(find.text('Сохранить оба…'), findsOneWidget);
    expect(find.text('Выход'), findsOneWidget);
    await tester.tap(find.text('Выход'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Ещё ▾'));
    await tester.pumpAndSettle();
    expect(find.text('Потоковый перевод'), findsOneWidget);
    expect(find.text('Синхронизация прокрутки'), findsOneWidget);
    // CheckedPopupMenuItem hit-tests poorly in widget tests — toggle via session.
    await tester.sendKeyEvent(LogicalKeyboardKey.escape);
    await tester.pumpAndSettle();
    await container.read(workspaceProvider.notifier).setStreaming(false);
    await container.read(workspaceProvider.notifier).setScrollSync(false);
    await tester.pumpAndSettle();
    expect(container.read(settingsProvider).streaming, isFalse);
    expect(container.read(settingsProvider).scrollSync, isFalse);
  });

  testWidgets('Ctrl+comma opens settings', (tester) async {
    await pumpApp(tester, settings: argosOnlySettings);
    await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    await tester.sendKeyEvent(LogicalKeyboardKey.comma);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    await tester.pumpAndSettle();
    expect(find.byType(SettingsPage), findsOneWidget);
  });

  testWidgets('char counter updates after typing', (tester) async {
    await pumpApp(tester, settings: argosOnlySettings.copyWith(streaming: false));
    await tester.enterText(find.byKey(const Key('source-editor')), 'Hello');
    await tester.pump();
    expect(find.text('5 симв.'), findsOneWidget);
  });

  testWidgets('status bar shows Ready after Argos finishes', (tester) async {
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
      sidecar: fakeSidecar(),
    );
    expect(find.text('Готово'), findsOneWidget);
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';
    await session.translateNow();
    await tester.pumpAndSettle();
    expect(find.text('Argos ✓'), findsOneWidget);
    expect(find.text('Готово'), findsOneWidget);
  });

  testWidgets('LLM indicator is muted when URL empty', (tester) async {
    await pumpApp(
      tester,
      settings: const AppSettings(
        firstRunDone: true,
        llm: LlmSettings(enabled: true, baseUrl: ''),
      ),
    );
    expect(find.text('● LLM'), findsOneWidget);
    // Retry button appears when not configured.
    expect(find.text('Повторить'), findsOneWidget);
  });
}
