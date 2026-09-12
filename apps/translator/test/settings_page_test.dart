import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:translator/core/theme/mockup_controls.dart';
import 'package:translator/features/session/workspace_controller.dart';
import 'package:translator/features/session/workspace_state.dart';
import 'package:translator/features/settings/model_picker_dialog.dart';
import 'package:translator/features/settings/settings_page.dart';
import 'package:translator/l10n/app_localizations.dart';
import 'package:translator/providers.dart';
import 'package:translator_core/translator_core.dart';

import 'support/harness.dart';

void main() {
  testWidgets('navigation shows intro and controls in all seven sections', (
    tester,
  ) async {
    await pumpApp(tester);
    await openSettings(tester);

    await goSection(tester, 'appearance');
    expect(
        find.text('Тема, масштаб текста и прозрачность окна.'), findsOneWidget);
    expect(find.byKey(const Key('settings-theme')), findsOneWidget);

    await goSection(tester, 'translation');
    expect(
        find.text('Потоковый перевод, задержки и кэш Argos.'), findsOneWidget);
    expect(find.byKey(const Key('settings-streaming')), findsOneWidget);

    await goSection(tester, 'llm');
    expect(find.text('Локальный сервер, OpenRouter или свой адрес.'),
        findsOneWidget);
    expect(find.byKey(const Key('settings-llm-enabled')), findsOneWidget);

    await goSection(tester, 'files');
    expect(find.text('Кодировка, суффиксы и лимиты файлов.'), findsOneWidget);
    expect(find.byKey(const Key('settings-encoding')), findsOneWidget);

    await goSection(tester, 'argos');
    expect(
      find.text(
          'Офлайн-модели Argos, установка из комплекта и папка packages.'),
      findsOneWidget,
    );
    expect(find.byKey(const Key('settings-bundle-on-start')), findsOneWidget);

    await goSection(tester, 'behavior');
    expect(find.text('Трей, горячие клавиши и буфер обмена.'), findsOneWidget);
    expect(find.byKey(const Key('settings-close-action')), findsOneWidget);

    await goSection(tester, 'about');
    expect(find.text('Версия, статус движков и пути к конфигурации.'),
        findsOneWidget);
    expect(find.text('Argos Translate'), findsWidgets);
  });

  testWidgets('appearance font and scale apply to source editor',
      (tester) async {
    final container = await pumpApp(tester);
    await openSettings(tester);
    await tester.tap(find.byKey(const Key('settings-editor-font')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Моноширинный').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('settings-font-scale')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('settings-ok')));
    await tester.pumpAndSettle();

    expect(find.byType(SettingsPage), findsNothing);
    final settings = container.read(settingsProvider);
    expect(settings.window.editorFont, 'mono');
    expect(settings.window.fontScale, closeTo(1.5, 0.05));
    final field = tester.widget<TextField>(
      find.descendant(
        of: find.byKey(const Key('source-editor')),
        matching: find.byType(TextField),
      ),
    );
    expect(field.style?.fontFamily, 'Consolas');
    expect(
      field.style?.fontSize,
      closeTo(
          TranslatorPalette.fontSizeEditor * settings.window.fontScale, 0.5),
    );
  });

  testWidgets('theme light Apply stays without cancel', (tester) async {
    await pumpApp(tester);
    await openSettings(tester);
    await tester.tap(find.byKey(const Key('settings-theme')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Светлая').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('settings-apply')));
    await tester.pumpAndSettle();
    expect(find.byType(SettingsPage), findsOneWidget);
    expect(
      Theme.of(tester.element(find.byType(SettingsPage))).brightness,
      Brightness.light,
    );
  });

  testWidgets('streaming off Apply and debounce 50 clamps to 100',
      (tester) async {
    final container = await pumpApp(tester);
    await openSettings(tester);
    await goSection(tester, 'translation');
    await tester.tap(find.byKey(const Key('settings-streaming')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('settings-debounce')), '50');
    await tester.pump();
    await tester.tap(find.byKey(const Key('settings-translation-cache')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('settings-cache-size')), findsOneWidget);
    await tester.tap(find.byKey(const Key('settings-apply')));
    await tester.pumpAndSettle();
    expect(container.read(settingsProvider).streaming, isFalse);
    expect(container.read(settingsProvider).debounceMs, 100);
    expect(container.read(settingsProvider).behavior.translationCacheEnabled,
        isTrue);
    await tester.tap(find.byKey(const Key('settings-ok')));
    await tester.pumpAndSettle();

    await tester.enterText(
        find.byKey(const Key('source-editor')), 'Hello world');
    await tester.pump(const Duration(milliseconds: 900));
    expect(container.read(workspaceProvider).argosBusy, isFalse);
    expect(container.read(settingsProvider).streaming, isFalse);
  });

  testWidgets('LLM local key disabled, OpenRouter warning, check banners', (
    tester,
  ) async {
    await pumpApp(
      tester,
      settings: const AppSettings(llm: LlmSettings(enabled: false)),
      llm: FakeLlmClient(),
    );
    await openSettings(tester);
    await goSection(tester, 'llm');
    final keyField = tester.widget<TextField>(
      find.descendant(
        of: find.byKey(const Key('settings-llm-key')),
        matching: find.byType(TextField),
      ),
    );
    expect(keyField.enabled, isFalse);
    expect(find.text('Для LOCAL ключ не нужен.'), findsOneWidget);

    await tester.ensureVisible(find.byKey(const Key('settings-llm-check')));
    await tester.tap(find.byKey(const Key('settings-llm-check')));
    await tester.pumpAndSettle();
    expect(find.text('Сначала включите перевод LLM.'), findsOneWidget);

    await tester.tap(find.byKey(const Key('settings-llm-enabled')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('settings-llm-check')));
    await tester.pumpAndSettle();
    expect(find.text('Соединение установлено'), findsOneWidget);

    await tester.tap(find.byKey(const Key('settings-llm-provider')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OpenRouter').last);
    await tester.pumpAndSettle();
    expect(find.text('Текст уходит в облако.'), findsOneWidget);
    expect(
      tester
          .widget<TextField>(
            find.descendant(
              of: find.byKey(const Key('settings-llm-key')),
              matching: find.byType(TextField),
            ),
          )
          .enabled,
      isTrue,
    );

    await tester.ensureVisible(find.byKey(const Key('settings-llm-advanced')));
    await tester.tap(find.byKey(const Key('settings-llm-advanced')));
    await tester.pumpAndSettle();
    await tester
        .ensureVisible(find.byKey(const Key('settings-llm-temperature')));
    expect(find.byKey(const Key('settings-llm-temperature')), findsOneWidget);

    await tester
        .ensureVisible(find.byKey(const Key('settings-llm-load-models')));
    await tester.tap(find.byKey(const Key('settings-llm-load-models')));
    await tester.pumpAndSettle();
    expect(find.text('Выберите модель'), findsOneWidget);
  });

  testWidgets('files suffix empty becomes _translated and encoding stays', (
    tester,
  ) async {
    final container = await pumpApp(tester);
    await openSettings(tester);
    await goSection(tester, 'files');
    await tester.enterText(find.byKey(const Key('settings-suffix')), '');
    await tester.tap(find.byKey(const Key('settings-encoding')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('UTF-8 с BOM').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('settings-apply')));
    await tester.pumpAndSettle();
    expect(container.read(settingsProvider).files.outputSuffix, '_translated');
    expect(container.read(settingsProvider).files.outputEncoding, 'utf-8-sig');
  });

  testWidgets('Argos without sidecar disables open packages', (tester) async {
    await pumpApp(tester);
    await openSettings(tester);
    await goSection(tester, 'argos');
    expect(find.textContaining('нет связи'), findsWidgets);
    expect(
      tester
          .widget<MockupButton>(find.byKey(const Key('settings-open-packages')))
          .onPressed,
      isNull,
    );
  });

  testWidgets('Argos with fake sidecar shows packages path', (tester) async {
    await pumpApp(tester, sidecar: fakeSidecar());
    await openSettings(tester);
    await goSection(tester, 'argos');
    expect(find.textContaining(r'C:\Argos\packages'), findsOneWidget);
    expect(
      tester
          .widget<MockupButton>(find.byKey(const Key('settings-open-packages')))
          .onPressed,
      isNotNull,
    );
  });

  testWidgets('behavior close action, hotkey and flags persist',
      (tester) async {
    final container = await pumpApp(tester);
    await openSettings(tester);
    await goSection(tester, 'behavior');
    await tester.tap(find.byKey(const Key('settings-close-action')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Выходить').last);
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('settings-hotkey')), 'ctrl+c');
    await tester.tap(find.byKey(const Key('settings-start-minimized')));
    await tester.tap(find.byKey(const Key('settings-restore-clipboard')));
    await tester.tap(find.byKey(const Key('settings-copy-hide')));
    await tester.ensureVisible(find.byKey(const Key('settings-triple-copy')));
    await tester.tap(find.byKey(const Key('settings-triple-copy')));
    await tester.pump();
    await tester.tap(find.byKey(const Key('settings-apply')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('settings-banner')), findsOneWidget);
    expect(find.textContaining('Хоткей не распознан'), findsOneWidget);
    final settings = container.read(settingsProvider);
    expect(settings.behavior.closeAction, 'exit');
    expect(settings.behavior.globalHotkey, isEmpty);
    expect(settings.behavior.startMinimizedToTray, isTrue);
    expect(settings.behavior.restoreClipboardAfterCapture, isFalse);
    expect(settings.behavior.minimizeToTrayOnCopyHide, isFalse);
    expect(settings.behavior.tripleCopyEnabled, isFalse);
  });

  testWidgets('footer Apply stays, Cancel restores LLM, OK pops',
      (tester) async {
    await pumpApp(
      tester,
      settings: const AppSettings(llm: LlmSettings(enabled: false)),
    );
    await openSettings(tester);
    await goSection(tester, 'llm');
    await tester.tap(find.byKey(const Key('settings-llm-enabled')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('settings-apply')));
    await tester.pumpAndSettle();
    expect(find.byType(SettingsPage), findsOneWidget);

    await tester.tap(find.byKey(const Key('settings-cancel')));
    await tester.pumpAndSettle();
    expect(find.byType(SettingsPage), findsNothing);

    await openSettings(tester);
    await tester.tap(find.byKey(const Key('settings-ok')));
    await tester.pumpAndSettle();
    expect(find.byType(SettingsPage), findsNothing);
  });

  testWidgets('Escape and system back cancel settings', (tester) async {
    await pumpApp(
      tester,
      settings: const AppSettings(llm: LlmSettings(enabled: false)),
    );
    await openSettings(tester);
    await goSection(tester, 'llm');
    await tester.tap(find.byKey(const Key('settings-llm-enabled')));
    await tester.pumpAndSettle();
    await tester.sendKeyEvent(LogicalKeyboardKey.escape);
    await tester.pumpAndSettle();
    expect(find.byType(SettingsPage), findsNothing);
    expect(
      tester
          .widget<Checkbox>(
            find.descendant(
              of: find.byKey(const Key('llm-enable')),
              matching: find.byType(Checkbox),
            ),
          )
          .value,
      isFalse,
    );

    await openSettings(tester);
    await tester.binding.handlePopRoute();
    await tester.pumpAndSettle();
    expect(find.byType(SettingsPage), findsNothing);
  });

  testWidgets('model picker filters list', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('ru'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) => TextButton(
            onPressed: () => showModelPickerDialog(
              context: context,
              models: const ['alpha', 'beta-llm', 'gamma'],
            ),
            child: const Text('open'),
          ),
        ),
      ),
    );
    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
    await tester.enterText(
        find.byKey(const Key('model-picker-search')), 'beta');
    await tester.pumpAndSettle();
    expect(find.text('beta-llm'), findsWidgets);
    expect(find.text('alpha'), findsNothing);
  });

  testWidgets('openPath over warn chars sets large-file hint', (tester) async {
    final container = await pumpApp(
      tester,
      settings: const AppSettings(
        files: FileSettings(largeFileWarnChars: 1000),
        llm: LlmSettings(enabled: false),
      ),
      sidecar: fakeSidecar(FakeSidecarOptions(decodeText: 'x' * 2000)),
    );
    await container
        .read(workspaceProvider.notifier)
        .openPath(r'C:\tmp\note.txt');
    await tester.pumpAndSettle();
    expect(container.read(workspaceProvider).hint, SessionHint.largeFile);
    expect(container.read(workspaceProvider).argosBusy, isFalse);
  });
}
