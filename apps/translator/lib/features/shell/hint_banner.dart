import 'package:flutter/material.dart';

import '../../core/theme/mockup_controls.dart';
import '../../l10n/app_localizations.dart';
import '../session/workspace_state.dart';

class HintBanner extends StatelessWidget {
  const HintBanner({
    super.key,
    required this.hint,
    required this.retry,
    required this.onClose,
    required this.onRetry,
  });

  final SessionHint hint;
  final HintRetry retry;
  final VoidCallback onClose;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    if (hint == SessionHint.none) {
      return const SizedBox.shrink();
    }
    final l10n = AppLocalizations.of(context);
    final palette =
        TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final isError = hint == SessionHint.llmConnection ||
        hint == SessionHint.llmNotConfigured ||
        hint == SessionHint.noEngine ||
        hint == SessionHint.installFailed ||
        hint == SessionHint.unsupportedFile;

    return Material(
      key: const Key('hint-banner'),
      color: isError
          ? palette.danger.withValues(alpha: 0.12)
          : palette.backgroundElevated,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: MockupLayout.space,
          vertical: MockupLayout.space,
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                _message(l10n),
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: isError ? palette.danger : palette.textPrimary,
                    ),
              ),
            ),
            if (retry != HintRetry.none)
              MockupButton(
                variant: MockupButtonVariant.ghost,
                label: l10n.retry,
                onPressed: onRetry,
              ),
            Semantics(
              button: true,
              label: l10n.clear,
              child: MockupButton(
                variant: MockupButtonVariant.ghost,
                icon: Icons.close,
                tooltip: l10n.clear,
                onPressed: onClose,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _message(AppLocalizations l10n) {
    switch (hint) {
      case SessionHint.none:
        return '';
      case SessionHint.llmNotConfigured:
        return l10n.llmNotConfigured;
      case SessionHint.llmConnection:
        return l10n.llmConnectionError;
      case SessionHint.unsupportedFile:
        return l10n.unsupportedFile;
      case SessionHint.openFileFirst:
        return l10n.openFileFirst;
      case SessionHint.saved:
        return l10n.saved;
      case SessionHint.noEngine:
        return l10n.noTranslationEngine;
      case SessionHint.noTranslation:
        return l10n.noTranslationToSave;
      case SessionHint.installFailed:
        return l10n.installFailed;
      case SessionHint.copied:
        return l10n.copied;
      case SessionHint.largeFile:
        return l10n.largeFileWarnHint;
      case SessionHint.engineRestarting:
        return l10n.engineRestarting;
    }
  }
}
