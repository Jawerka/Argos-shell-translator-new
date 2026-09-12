import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:translator/features/session/document_files.dart';
import 'package:translator/features/session/workspace_controller.dart';
import 'package:translator/features/session/workspace_state.dart';
import 'package:translator/features/settings/settings_page.dart';
import 'package:translator_core/translator_core.dart';

import 'support/harness.dart';

void main() {
  testWidgets('translateNow fills Argos text and shows done badge', (
    tester,
  ) async {
    final sidecar = fakeSidecar();
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
      sidecar: sidecar,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';
    await session.translateNow();
    await tester.pumpAndSettle();

    expect(session.argosController.text, 'Привет');
    expect(container.read(workspaceProvider).argosStatus, EngineRunStatus.done);
    expect(find.text('Argos ✓'), findsOneWidget);
    expect(find.text('Готово'), findsOneWidget);
    expect(sidecar.fakeState.translateCalls, greaterThan(0));
  });

  testWidgets('Translate button and Ctrl+Enter start Argos', (tester) async {
    final sidecar = fakeSidecar();
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
      sidecar: sidecar,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';

    await tester.tap(find.text('Перевести'));
    await tester.pumpAndSettle();
    expect(session.argosController.text, 'Привет');

    session.argosController.clear();
    final before = sidecar.fakeState.translateCalls;
    await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    await tester.pumpAndSettle();
    expect(sidecar.fakeState.translateCalls, greaterThan(before));
    expect(session.argosController.text, 'Привет');
  });

  testWidgets('AUTO detect shows EN chip without replacing combo', (
    tester,
  ) async {
    final sidecar = fakeSidecar(FakeSidecarOptions(detectCode: 'en'));
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings.copyWith(langFrom: 'auto', langTo: 'ru'),
      sidecar: sidecar,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';
    await session.translateNow();
    await tester.pumpAndSettle();

    expect(container.read(workspaceProvider).langFrom, 'auto');
    expect(container.read(workspaceProvider).detectedLang, 'en');
    expect(find.byKey(const Key('detected-lang')), findsOneWidget);
    expect(find.text('EN → RU'), findsOneWidget);
  });

  testWidgets('streaming debounce waits before Argos call', (tester) async {
    final sidecar = fakeSidecar();
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings.copyWith(
        streaming: true,
        debounceMs: 100,
      ),
      sidecar: sidecar,
    );
    await tester.enterText(find.byKey(const Key('source-editor')), 'Hello world');
    await tester.pump();
    expect(sidecar.fakeState.translateCalls, 0);

    await tester.pump(const Duration(milliseconds: 120));
    await tester.pumpAndSettle();
    expect(sidecar.fakeState.translateCalls, greaterThan(0));
    expect(
      container.read(workspaceProvider.notifier).argosController.text,
      'Привет',
    );
  });

  testWidgets('streaming off does not translate on type', (tester) async {
    final sidecar = fakeSidecar();
    await pumpApp(
      tester,
      settings: argosOnlySettings.copyWith(streaming: false),
      sidecar: sidecar,
    );
    await tester.enterText(find.byKey(const Key('source-editor')), 'Hello world');
    await tester.pump(const Duration(milliseconds: 900));
    expect(sidecar.fakeState.translateCalls, 0);
  });

  testWidgets('translateNow no-ops for short text', (tester) async {
    final sidecar = fakeSidecar();
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
      sidecar: sidecar,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'H';
    await session.translateNow();
    await tester.pumpAndSettle();
    expect(sidecar.fakeState.translateCalls, 0);
  });

  testWidgets('no sidecar and LLM off shows no-engine hint', (tester) async {
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';
    await session.translateNow();
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).hint, SessionHint.noEngine);
    expect(find.byKey(const Key('hint-banner')), findsOneWidget);
    expect(find.text('Нет движка перевода'), findsOneWidget);
  });

  testWidgets('no models overlay and installBundle clears it', (tester) async {
    final sidecar = fakeSidecar(FakeSidecarOptions(pairs: const []));
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
      sidecar: sidecar,
    );
    await tester.pumpAndSettle();
    expect(find.text('Нет моделей Argos'), findsOneWidget);
    expect(find.text('Установить модели'), findsOneWidget);

    await container.read(workspaceProvider.notifier).installBundle();
    await tester.pumpAndSettle();
    expect(sidecar.fakeState.installCalls, 1);
    expect(sidecar.fakeState.lastInstallBundle, isTrue);
    expect(container.read(workspaceProvider).hasArgosModels, isTrue);
    expect(find.text('Нет моделей Argos'), findsNothing);
  });

  testWidgets('Argos error event sets error badge', (tester) async {
    final sidecar = fakeSidecar(
      FakeSidecarOptions(translateMode: FakeTranslateMode.error),
    );
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
      sidecar: sidecar,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';
    await session.translateNow();
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).argosStatus, EngineRunStatus.error);
    expect(find.text('Argos ошибка'), findsOneWidget);
  });

  testWidgets('Argos missing pair shows error overlay and tooltip', (
    tester,
  ) async {
    final sidecar = fakeSidecar(
      FakeSidecarOptions(translateMode: FakeTranslateMode.missingPair),
    );
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
      sidecar: sidecar,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';
    await session.translateNow();
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).argosStatus, EngineRunStatus.error);
    expect(container.read(workspaceProvider).argosError, 'Нет модели nl→ru');
    expect(find.text('Argos ошибка'), findsOneWidget);
    expect(find.text('Нет модели nl→ru'), findsOneWidget);
    expect(find.byTooltip('Нет модели nl→ru'), findsOneWidget);
    expect(find.text('Введите текст слева'), findsNothing);
  });

  testWidgets('Stop after Argos chunk keeps text and clears busy', (
    tester,
  ) async {
    final sidecar = fakeSidecar(
      FakeSidecarOptions(translateMode: FakeTranslateMode.cancelled),
    );
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
      sidecar: sidecar,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';
    await session.translateNow();
    await tester.pumpAndSettle();
    expect(session.argosController.text, 'Привет');
    expect(container.read(workspaceProvider).argosBusy, isFalse);

    session.argosController.text = 'частичный';
    await session.stop();
    await tester.pumpAndSettle();
    expect(session.argosController.text, 'частичный');
    expect(container.read(workspaceProvider).argosBusy, isFalse);
  });

  testWidgets('LLM stream fills tab and shows done badge', (tester) async {
    final llm = FakeLlmClient();
    final container = await pumpApp(
      tester,
      settings: const AppSettings(
        firstRunDone: true,
        llm: LlmSettings(
          enabled: true,
          baseUrl: 'http://127.0.0.1:1234/v1',
        ),
      ),
      llm: llm,
      sidecar: fakeSidecar(),
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';
    await session.setActiveTab('llm');
    await session.translateNow();
    await tester.pumpAndSettle();

    expect(session.llmController.text, 'Привет');
    expect(container.read(workspaceProvider).llmStatus, EngineRunStatus.done);
    expect(find.text('LLM ✓'), findsOneWidget);
    expect(llm.translateCalls, greaterThan(0));
  });

  testWidgets('LLM missing URL shows not configured and retry opens settings', (
    tester,
  ) async {
    final container = await pumpApp(
      tester,
      settings: const AppSettings(
        firstRunDone: true,
        llm: LlmSettings(enabled: true, baseUrl: ''),
      ),
      llm: FakeLlmClient(),
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';
    await session.translateNow();
    await tester.pumpAndSettle();

    expect(container.read(workspaceProvider).hint, SessionHint.llmNotConfigured);
    expect(find.text('LLM не задан'), findsOneWidget);
    expect(find.text('Повторить'), findsWidgets);

    await tester.tap(find.text('Повторить').first);
    await tester.pumpAndSettle();
    expect(find.byType(SettingsPage), findsOneWidget);
  });

  testWidgets('LLM connection error retry calls translate again', (
    tester,
  ) async {
    final llm = FakeLlmClient(mode: FakeLlmMode.error);
    final container = await pumpApp(
      tester,
      settings: const AppSettings(
        firstRunDone: true,
        llm: LlmSettings(
          enabled: true,
          baseUrl: 'http://127.0.0.1:1234/v1',
        ),
      ),
      llm: llm,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world';
    await session.translateNow();
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).hint, SessionHint.llmConnection);
    expect(find.text('LLM ошибка'), findsWidgets);

    final before = llm.translateCalls;
    await session.retryLlm();
    await tester.pumpAndSettle();
    expect(llm.translateCalls, greaterThan(before));
  });

  testWidgets('openDroppedPath rejects unsupported extension', (tester) async {
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
      sidecar: fakeSidecar(),
    );
    await container
        .read(workspaceProvider.notifier)
        .openDroppedPath(r'C:\tmp\note.docx');
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).hint, SessionHint.unsupportedFile);
  });

  testWidgets('openPath without sidecar shows no engine', (tester) async {
    final container = await pumpApp(tester, settings: argosOnlySettings);
    await container
        .read(workspaceProvider.notifier)
        .openPath(r'C:\tmp\note.txt');
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).hint, SessionHint.noEngine);
  });

  testWidgets('openPath decode triggers auto translate', (tester) async {
    final sidecar = fakeSidecar(
      FakeSidecarOptions(decodeText: 'Hello world'),
    );
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
      sidecar: sidecar,
    );
    await container
        .read(workspaceProvider.notifier)
        .openPath(r'C:\tmp\note.txt');
    await tester.pumpAndSettle();
    expect(
      container.read(workspaceProvider.notifier).sourceController.text,
      'Hello world',
    );
    expect(
      container.read(workspaceProvider.notifier).argosController.text,
      'Привет',
    );
    expect(sidecar.fakeState.translateCalls, greaterThan(0));
  });

  testWidgets('saveTranslation empty shows no translation hint', (
    tester,
  ) async {
    final container = await pumpApp(tester, settings: argosOnlySettings);
    await container.read(workspaceProvider.notifier).saveTranslation();
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).hint, SessionHint.noTranslation);
  });

  testWidgets('saveBoth without document shows open file first', (
    tester,
  ) async {
    final container = await pumpApp(tester, settings: argosOnlySettings);
    final session = container.read(workspaceProvider.notifier);
    session.argosController.text = 'x';
    await session.saveBoth();
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).hint, SessionHint.openFileFirst);
  });

  test('saveBoth output paths write argos and llm files', () async {
    final dir = await Directory.systemTemp.createTemp('argos_sb_');
    addTearDown(() => dir.delete(recursive: true));
    final docPath = '${dir.path}${Platform.pathSeparator}note.txt';
    final argosPath = suggestedTranslationPath(
      docPath,
      suffix: '_translated',
      engine: 'argos',
    );
    final llmPath = suggestedTranslationPath(
      docPath,
      suffix: '_translated',
      engine: 'llm',
    );
    await writeEncodedTextFile(
      path: argosPath,
      content: 'argos-out',
      encoding: 'utf-8',
    );
    await writeEncodedTextFile(
      path: llmPath,
      content: 'llm-out',
      encoding: 'utf-8',
    );
    expect(await File(argosPath).readAsString(), 'argos-out');
    expect(await File(llmPath).readAsString(), 'llm-out');
  });

  testWidgets('clear source and translation reset controllers', (tester) async {
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings.copyWith(streaming: false),
      sidecar: fakeSidecar(),
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'source text';
    session.argosController.text = 'перевод';

    session.clearSource();
    await tester.pump();
    expect(session.sourceController.text, isEmpty);

    session.argosController.text = 'ещё';
    session.clearTranslation();
    await tester.pump();
    expect(session.argosController.text, isEmpty);
  });

  testWidgets('selection change does not retrigger translate', (tester) async {
    final sidecar = fakeSidecar();
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings.copyWith(
        streaming: true,
        debounceMs: 80,
      ),
      sidecar: sidecar,
    );
    await tester.enterText(
      find.byKey(const Key('source-editor')),
      'Hello world',
    );
    await tester.pump(const Duration(milliseconds: 120));
    await tester.pumpAndSettle();
    final calls = sidecar.fakeState.translateCalls;
    expect(calls, greaterThan(0));

    final session = container.read(workspaceProvider.notifier);
    session.sourceController.selection = const TextSelection.collapsed(offset: 0);
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pumpAndSettle();
    expect(sidecar.fakeState.translateCalls, calls);
  });

  testWidgets('AUTO russian text sends ru→en to Argos and LLM', (tester) async {
    final sidecar = fakeSidecar(FakeSidecarOptions(detectCode: 'ru'));
    final llm = FakeLlmClient();
    final container = await pumpApp(
      tester,
      settings: const AppSettings(
        firstRunDone: true,
        langFrom: 'auto',
        langTo: 'ru',
        llm: LlmSettings(
          enabled: true,
          provider: 'local',
          baseUrl: 'http://127.0.0.1:8080/v1',
          model: 'test',
        ),
      ),
      sidecar: sidecar,
      llm: llm,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Привет, это достаточно длинный текст';
    await session.translateNow();
    await tester.pumpAndSettle();

    expect(sidecar.fakeState.translateBodies, isNotEmpty);
    expect(sidecar.fakeState.translateBodies.last['from'], 'ru');
    expect(sidecar.fakeState.translateBodies.last['to'], 'en');
    expect(llm.lastFromCode, 'ru');
    expect(llm.lastToCode, 'en');
    expect(container.read(workspaceProvider).detectedLang, 'ru');
    expect(find.text('RU → EN'), findsOneWidget);
  });

  testWidgets('AUTO english with detect=nl snaps to EN → RU', (tester) async {
    final sidecar = fakeSidecar(
      FakeSidecarOptions(
        detectCode: 'nl',
        pairs: const ['en->ru', 'ru->en'],
      ),
    );
    final llm = FakeLlmClient();
    final container = await pumpApp(
      tester,
      settings: const AppSettings(
        firstRunDone: true,
        langFrom: 'auto',
        langTo: 'ru',
        llm: LlmSettings(
          enabled: true,
          provider: 'local',
          baseUrl: 'http://127.0.0.1:8080/v1',
          model: 'test',
        ),
      ),
      sidecar: sidecar,
      llm: llm,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text =
        'This is a reasonably long English sentence used for language detection.';
    await session.translateNow();
    await tester.pumpAndSettle();

    expect(sidecar.fakeState.translateBodies, isNotEmpty);
    expect(sidecar.fakeState.translateBodies.last['from'], 'en');
    expect(sidecar.fakeState.translateBodies.last['to'], 'ru');
    expect(llm.lastFromCode, 'en');
    expect(llm.lastToCode, 'ru');
    expect(container.read(workspaceProvider).detectedLang, 'en');
    expect(find.text('EN → RU'), findsOneWidget);
  });

  testWidgets('translateNow starts Argos and LLM together', (tester) async {
    final sidecar = fakeSidecar();
    final llm = FakeLlmClient();
    final container = await pumpApp(
      tester,
      settings: const AppSettings(
        firstRunDone: true,
        llm: LlmSettings(
          enabled: true,
          provider: 'local',
          baseUrl: 'http://127.0.0.1:8080/v1',
          model: 'test',
        ),
      ),
      sidecar: sidecar,
      llm: llm,
    );
    final session = container.read(workspaceProvider.notifier);
    session.sourceController.text = 'Hello world from both engines';
    await session.translateNow();
    await tester.pumpAndSettle();
    expect(sidecar.fakeState.translateCalls, greaterThan(0));
    expect(llm.translateCalls, greaterThan(0));
  });

  testWidgets('Ctrl+Shift+X swaps languages, Alt+Shift does not', (tester) async {
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings.copyWith(langFrom: 'en', langTo: 'ru'),
      sidecar: fakeSidecar(),
    );
    await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    await tester.sendKeyDownEvent(LogicalKeyboardKey.shiftLeft);
    await tester.sendKeyEvent(LogicalKeyboardKey.keyX);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.shiftLeft);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).langFrom, 'ru');
    expect(container.read(workspaceProvider).langTo, 'en');

    await tester.sendKeyDownEvent(LogicalKeyboardKey.altLeft);
    await tester.sendKeyDownEvent(LogicalKeyboardKey.shiftLeft);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.shiftLeft);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.altLeft);
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).langFrom, 'ru');
    expect(container.read(workspaceProvider).langTo, 'en');
  });

  testWidgets('Ctrl+Enter and Esc work while source editor is focused', (
    tester,
  ) async {
    final sidecar = fakeSidecar();
    final container = await pumpApp(
      tester,
      settings: argosOnlySettings,
      sidecar: sidecar,
    );
    await tester.tap(find.byKey(const Key('source-editor')));
    await tester.enterText(
      find.byKey(const Key('source-editor')),
      'Hello world',
    );
    await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    await tester.pumpAndSettle();
    expect(sidecar.fakeState.translateCalls, greaterThan(0));

    await tester.sendKeyEvent(LogicalKeyboardKey.escape);
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).argosBusy, isFalse);
  });
}
