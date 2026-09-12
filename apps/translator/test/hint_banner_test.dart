import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:translator/core/theme/translator_theme.dart';
import 'package:translator/features/session/workspace_state.dart';
import 'package:translator/features/shell/hint_banner.dart';
import 'package:translator/l10n/app_localizations.dart';

void main() {
  Future<void> pumpBanner(
    WidgetTester tester, {
    required SessionHint hint,
    HintRetry retry = HintRetry.none,
    VoidCallback? onClose,
    VoidCallback? onRetry,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('ru'),
        theme: TranslatorTheme.dark(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(
          body: HintBanner(
            hint: hint,
            retry: retry,
            onClose: onClose ?? () {},
            onRetry: onRetry ?? () {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  const cases = <(SessionHint, String)>[
    (SessionHint.llmNotConfigured, 'LLM не задан'),
    (SessionHint.llmConnection, 'LLM ошибка'),
    (SessionHint.unsupportedFile, 'Этот тип файла не поддерживается'),
    (SessionHint.openFileFirst, 'Сначала откройте файл'),
    (SessionHint.saved, 'Сохранено'),
    (SessionHint.noEngine, 'Нет движка перевода'),
    (SessionHint.noTranslation, 'Нет перевода для сохранения'),
    (SessionHint.installFailed, 'Не удалось установить модели'),
    (SessionHint.copied, 'Скопировано'),
    (
      SessionHint.largeFile,
      'Файл большой: автоперевод не запущен. Нажмите «Перевести» или «Повтор».',
    ),
  ];

  for (final entry in cases) {
    testWidgets('hint ${entry.$1.name} shows message', (tester) async {
      await pumpBanner(tester, hint: entry.$1);
      expect(find.byKey(const Key('hint-banner')), findsOneWidget);
      expect(find.text(entry.$2), findsOneWidget);
    });
  }

  testWidgets('none hint renders nothing', (tester) async {
    await pumpBanner(tester, hint: SessionHint.none);
    expect(find.byKey(const Key('hint-banner')), findsNothing);
  });

  testWidgets('close button calls onClose', (tester) async {
    var closed = false;
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('ru'),
        theme: TranslatorTheme.dark(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(
          body: HintBanner(
            hint: SessionHint.copied,
            retry: HintRetry.none,
            onClose: () => closed = true,
            onRetry: () {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Очистить'));
    await tester.pumpAndSettle();
    expect(closed, isTrue);
  });

  testWidgets('retry button shown and calls onRetry', (tester) async {
    var retried = false;
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('ru'),
        theme: TranslatorTheme.dark(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(
          body: HintBanner(
            hint: SessionHint.llmConnection,
            retry: HintRetry.llm,
            onClose: () {},
            onRetry: () => retried = true,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Повторить'), findsOneWidget);
    await tester.tap(find.text('Повторить'));
    await tester.pumpAndSettle();
    expect(retried, isTrue);
  });
}
