import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:translator_core/translator_core.dart';

import '../../core/theme/mockup_controls.dart';
import '../../l10n/app_localizations.dart';
import '../../providers.dart';
import '../session/workspace_controller.dart';
import '../session/workspace_state.dart';
import 'main_toolbar.dart';

class StatusBar extends ConsumerWidget {
  const StatusBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final settings = ref.watch(settingsProvider);
    final session = ref.watch(workspaceProvider);

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: MockupLayout.footerPadH,
        vertical: MockupLayout.footerPadV,
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              _statusText(l10n, session),
              style: TextStyle(
                fontSize: TranslatorPalette.fontSizeUi,
                color: palette.textMuted,
              ),
            ),
          ),
          _LlmIndicator(settings: settings, session: session),
        ],
      ),
    );
  }

  String _statusText(AppLocalizations l10n, WorkspaceState session) {
    final parts = <String>[];
    if (session.argosBusy) {
      if (session.argosTotal > 0) {
        parts.add(l10n.progressArgos(session.argosDone, session.argosTotal));
      } else {
        parts.add(l10n.progressArgosBusy);
      }
    }
    if (session.llmBusy) {
      if (session.llmTotal > 0) {
        parts.add(l10n.progressLlm(session.llmDone, session.llmTotal));
      } else {
        parts.add(l10n.progressLlmBusy);
      }
    }
    if (parts.isEmpty) {
      return l10n.statusReady;
    }
    return parts.join(' · ');
  }
}

class _LlmIndicator extends ConsumerWidget {
  const _LlmIndicator({required this.settings, required this.session});

  final AppSettings settings;
  final WorkspaceState session;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final cfgErr = llmConfigError(
      ref.read(llmKeyStoreProvider).attachCached(settings.llm),
    );
    final notConfigured = cfgErr != null;
    final connectionError = session.llmReachable == false && !notConfigured;

    Color color = palette.success;
    if (notConfigured) {
      color = palette.textMuted;
    } else if (connectionError) {
      color = palette.danger;
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          l10n.llmConnected,
          style: TextStyle(
            fontSize: TranslatorPalette.fontSizeUi,
            color: color,
          ),
        ),
        if (connectionError || notConfigured) ...[
          const SizedBox(width: MockupLayout.space),
          MockupButton(
            variant: MockupButtonVariant.ghost,
            label: l10n.retry,
            onPressed: () {
              if (notConfigured) {
                openSettingsPage(context);
              } else {
                ref.read(workspaceProvider.notifier).retryLlm();
              }
            },
          ),
        ],
      ],
    );
  }
}
