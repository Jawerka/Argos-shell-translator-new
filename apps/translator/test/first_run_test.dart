import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:translator/core/theme/translator_theme.dart';
import 'package:translator/features/onboarding/first_run_page.dart';
import 'package:translator/l10n/app_localizations.dart';
import 'package:translator/providers.dart';
import 'package:translator_core/translator_core.dart';

import 'support/harness.dart';

void main() {
  test('first-run gate skips wizard in tests and when sidecar is skipped', () {
    expect(
      shouldShowFirstRun(
        firstRunDone: false,
        skipSidecar: true,
        inWidgetTest: true,
        inFlutterTest: true,
      ),
      isFalse,
    );
    expect(
      shouldShowFirstRun(
        firstRunDone: false,
        skipSidecar: false,
        inWidgetTest: false,
        inFlutterTest: false,
      ),
      isTrue,
    );
    expect(
      shouldShowFirstRun(
        firstRunDone: true,
        skipSidecar: false,
        inWidgetTest: false,
        inFlutterTest: false,
      ),
      isFalse,
    );
  });

  Future<ProviderContainer> pumpWizard(
    WidgetTester tester, {
    AppSettings? settings,
    SidecarClient? sidecar,
  }) async {
    tester.view.physicalSize = const Size(1400, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    late ProviderContainer container;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          if (settings != null)
            settingsProvider.overrideWith(() => SettingsController(settings)),
          if (sidecar != null)
            sidecarClientProvider.overrideWith((ref) => sidecar),
        ],
        child: Builder(
          builder: (context) {
            container = ProviderScope.containerOf(context);
            return MaterialApp(
              theme: TranslatorTheme.dark(),
              locale: const Locale('ru'),
              localizationsDelegates: AppLocalizations.localizationsDelegates,
              supportedLocales: AppLocalizations.supportedLocales,
              home: const FirstRunWizard(),
            );
          },
        ),
      ),
    );
    await tester.pumpAndSettle();
    return container;
  }

  testWidgets('FirstRunWizard completes and calls onDone', (tester) async {
    tester.view.physicalSize = const Size(1400, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    var done = false;
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: TranslatorTheme.dark(),
          locale: const Locale('ru'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: FirstRunWizard(onDone: () => done = true),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Добро пожаловать'), findsOneWidget);
    expect(find.text('Тема'), findsWidgets);
    expect(find.textContaining('192.168.88.41'), findsNothing);

    await tester.tap(find.byKey(const Key('first-run-continue')));
    await tester.pumpAndSettle();
    expect(find.text('Модели Argos'), findsOneWidget);

    await tester.tap(find.byKey(const Key('first-run-skip')));
    await tester.pumpAndSettle();
    expect(find.text('LLM опционально'), findsOneWidget);
    expect(find.textContaining('192.168.88.41'), findsNothing);

    await tester.tap(find.byKey(const Key('first-run-skip')));
    await tester.pumpAndSettle();
    expect(find.text('Закрытие в трей'), findsOneWidget);

    await tester.tap(find.byKey(const Key('first-run-finish')));
    await tester.pumpAndSettle();
    expect(done, isTrue);
  });

  testWidgets('theme light preview updates settings theme', (tester) async {
    final container = await pumpWizard(tester);
    await tester.tap(find.byKey(const Key('first-run-theme-light')));
    await tester.pumpAndSettle();
    expect(container.read(settingsProvider).window.theme, 'light');
  });

  testWidgets('models step without sidecar shows no engine', (tester) async {
    await pumpWizard(tester);
    await tester.tap(find.byKey(const Key('first-run-continue')));
    await tester.pumpAndSettle();
    expect(find.text('Нет движка перевода'), findsOneWidget);
  });

  testWidgets('models install bundle advances to LLM step', (tester) async {
    final sidecar = fakeSidecar(FakeSidecarOptions(pairs: const []));
    await pumpWizard(tester, sidecar: sidecar);
    await tester.tap(find.byKey(const Key('first-run-continue')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('first-run-install')));
    await tester.pumpAndSettle();
    expect(sidecar.fakeState.installCalls, 1);
    expect(sidecar.fakeState.lastInstallBundle, isTrue);
    expect(find.text('LLM опционально'), findsOneWidget);
  });

  testWidgets('OpenRouter shows cloud warning and LOCAL has no LAN IP', (
    tester,
  ) async {
    await pumpWizard(tester);
    await tester.tap(find.byKey(const Key('first-run-continue')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('first-run-skip')));
    await tester.pumpAndSettle();

    expect(find.textContaining('192.168.88.41'), findsNothing);

    // Provider dropdown — SettingsDropdown without key; tap LOCAL area then OpenRouter.
    await tester.tap(find.text('LOCAL'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OpenRouter').last);
    await tester.pumpAndSettle();
    expect(find.text('Текст уходит в облако.'), findsOneWidget);
  });

  testWidgets('tray exit finish sets firstRunDone and closeAction', (
    tester,
  ) async {
    final container = await pumpWizard(tester);
    await tester.tap(find.byKey(const Key('first-run-continue')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('first-run-skip')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('first-run-skip')));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('first-run-close-exit')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('first-run-finish')));
    await tester.pumpAndSettle();

    final settings = container.read(settingsProvider);
    expect(settings.firstRunDone, isTrue);
    expect(settings.behavior.closeAction, 'exit');
  });
}
