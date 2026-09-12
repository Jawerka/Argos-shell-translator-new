import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:translator/app.dart';
import 'package:translator/core/theme/translator_theme.dart';
import 'package:translator/features/onboarding/first_run_page.dart';
import 'package:translator/features/session/workspace_controller.dart';
import 'package:translator/features/settings/settings_page.dart';
import 'package:translator/features/shell/main_split.dart';
import 'package:translator/providers.dart';
import 'package:translator_core/translator_core.dart';

void main() {
  Future<void> pumpApp(
    WidgetTester tester, {
    AppSettings? settings,
  }) async {
    tester.view.physicalSize = const Size(1400, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          if (settings != null)
            settingsProvider.overrideWith(() => SettingsController(settings)),
        ],
        child: const TranslatorApp(
          skipDesktopShell: true,
          skipSidecar: true,
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('empty split shell builds without sidecar', (tester) async {
    await pumpApp(tester);

    expect(find.text('Перевести'), findsOneWidget);
    expect(find.text('Исходный текст'), findsNothing);
    expect(find.text('Перевод'), findsNothing);
    expect(find.textContaining('симв.'), findsOneWidget);
    expect(find.text('Ещё ▾'), findsOneWidget);
    expect(find.text('Копир. и скрыть'), findsOneWidget);
    expect(find.byKey(const Key('llm-enable')), findsOneWidget);
    expect(find.text('Введите текст слева'), findsOneWidget);
    expect(find.text('Готово'), findsOneWidget);
    expect(find.byType(MainSplit), findsOneWidget);
    expect(find.byType(FirstRunWizard), findsNothing);
  });

  testWidgets('toolbar has translate and stop', (tester) async {
    await pumpApp(tester);

    expect(find.text('Перевести'), findsOneWidget);
    expect(find.text('Стоп'), findsOneWidget);
    expect(find.byKey(const Key('source-editor')), findsOneWidget);
  });

  testWidgets('LLM checkbox is off when llm is disabled', (tester) async {
    await pumpApp(
      tester,
      settings: const AppSettings(llm: LlmSettings(enabled: false)),
    );

    final checkbox = tester.widget<Checkbox>(
      find.descendant(
        of: find.byKey(const Key('llm-enable')),
        matching: find.byType(Checkbox),
      ),
    );
    expect(checkbox.value, isFalse);
    expect(find.text('Введите текст слева'), findsOneWidget);
  });

  testWidgets('boot error screen shows open-log action', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: TranslatorApp(
          skipDesktopShell: true,
          skipSidecar: true,
          initialError: 'sidecar down',
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Не удалось запустить'), findsOneWidget);
    expect(find.text('sidecar down'), findsOneWidget);
    expect(find.text('Открыть лог'), findsOneWidget);
  });

  testWidgets('settings page shows seven sections and footer', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.byTooltip('Настройки'));
    await tester.pumpAndSettle();
    expect(find.text('Настройки'), findsWidgets);
    expect(find.text('Внешний вид'), findsOneWidget);
    expect(find.text('Перевод'), findsWidgets);
    expect(find.text('LLM'), findsWidgets);
    expect(find.text('Файлы'), findsOneWidget);
    expect(find.text('Argos'), findsWidgets);
    expect(find.text('Поведение'), findsOneWidget);
    expect(find.text('О программе'), findsOneWidget);
    expect(find.text('ОК'), findsOneWidget);
    expect(find.text('Применить'), findsOneWidget);
    expect(find.text('Отмена'), findsOneWidget);
    expect(find.text('Тема:'), findsOneWidget);
    expect(
      find.text('Тема, масштаб текста и прозрачность окна.'),
      findsOneWidget,
    );
  });

  testWidgets('appearance section shows theme control', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.byTooltip('Настройки'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('settings-nav-appearance')));
    await tester.pumpAndSettle();
    expect(find.text('Тема:'), findsOneWidget);
    expect(find.text('Тёмная'), findsOneWidget);
  });

  testWidgets('theme dropdown previews light mode and cancel restores', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.byTooltip('Настройки'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('settings-theme')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Светлая').last);
    await tester.pumpAndSettle();
    expect(
      Theme.of(tester.element(find.byType(SettingsPage))).brightness,
      Brightness.light,
    );
    await tester.tap(find.text('Отмена'));
    await tester.pumpAndSettle();
    expect(
      Theme.of(tester.element(find.byType(MainSplit))).brightness,
      Brightness.dark,
    );
  });

  testWidgets('opening settings without apply keeps LLM tab hidden', (tester) async {
    await pumpApp(
      tester,
      settings: const AppSettings(llm: LlmSettings(enabled: false)),
    );

    await tester.tap(find.byTooltip('Настройки'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('settings-nav-llm')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Использовать LLM-перевод'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Отмена'));
    await tester.pumpAndSettle();

    expect(find.text('Использовать LLM-перевод'), findsNothing);
    final checkbox = tester.widget<Checkbox>(
      find.descendant(
        of: find.byKey(const Key('llm-enable')),
        matching: find.byType(Checkbox),
      ),
    );
    expect(checkbox.value, isFalse);
    expect(find.text('Введите текст слева'), findsOneWidget);
  });

  testWidgets('Esc stops and keeps partial translation text', (tester) async {
    await pumpApp(tester);

    final container = ProviderScope.containerOf(
      tester.element(find.byType(MainSplit)),
    );
    final session = container.read(workspaceProvider.notifier);
    session.argosController.text = 'частичный перевод';

    await tester.sendKeyEvent(LogicalKeyboardKey.escape);
    await tester.pumpAndSettle();

    expect(session.argosController.text, 'частичный перевод');
    expect(container.read(workspaceProvider).argosBusy, isFalse);
    expect(container.read(workspaceProvider).llmBusy, isFalse);
  });

  testWidgets('Ctrl+S does not swap languages', (tester) async {
    await pumpApp(
      tester,
      settings: const AppSettings(langFrom: 'en', langTo: 'ru'),
    );

    final container = ProviderScope.containerOf(
      tester.element(find.byType(MainSplit)),
    );
    container.read(workspaceProvider.notifier).argosController.text = 'saved text';

    await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    await tester.sendKeyEvent(LogicalKeyboardKey.keyS);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    await tester.pumpAndSettle();

    final state = container.read(workspaceProvider);
    expect(state.langFrom, 'en');
    expect(state.langTo, 'ru');
  });

  testWidgets('source editor inset has no Material hover and control radius', (
    tester,
  ) async {
    await pumpApp(tester);

    final field = tester.widget<TextField>(
      find.descendant(
        of: find.byKey(const Key('source-editor')),
        matching: find.byType(TextField),
      ),
    );
    final decoration = field.decoration!;
    expect(decoration.hoverColor, Colors.transparent);
    expect(decoration.focusColor, Colors.transparent);

    final border = decoration.enabledBorder;
    expect(border, isA<OutlineInputBorder>());
    final outline = border! as OutlineInputBorder;
    expect(outline.borderRadius, BorderRadius.circular(TranslatorPalette.radiusControl));
    expect(outline.borderSide, BorderSide.none);
  });

  test('theme tokens match ui-mockups CSS', () {
    expect(TranslatorPalette.dark.primary, const Color(0xFF3890B5));
    expect(TranslatorPalette.dark.primaryHover, const Color(0xFF0F92E6));
    expect(TranslatorPalette.dark.background, const Color(0xFF0F1115));
    expect(TranslatorPalette.dark.surface, const Color(0xFF1B2230));
    expect(TranslatorPalette.dark.border, const Color(0xFF202A38));
    expect(TranslatorPalette.dark.textEditor, const Color(0xFFB8C4D4));
    expect(TranslatorPalette.radiusControl, 3);
    expect(TranslatorPalette.radiusCard, 0);
    expect(TranslatorPalette.fontSizeUi, 13);
    expect(MockupLayout.btnH, 30);
    expect(MockupLayout.btnIconW, 40);
    expect(MockupLayout.btnPrimaryW, 100);
    expect(MockupLayout.btnAccentWideW, 170);
    expect(MockupLayout.settingsSidebarW, 170);
    expect(MockupLayout.settingsLabelW, 160);
    expect(TranslatorTheme.dark().colorScheme.primary, const Color(0xFF3890B5));
  });
}
