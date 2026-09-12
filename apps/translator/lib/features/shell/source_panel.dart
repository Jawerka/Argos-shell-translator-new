import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/mockup_controls.dart';
import '../../l10n/app_localizations.dart';
import '../../providers.dart';
import '../session/workspace_controller.dart';
import 'editor_style.dart';
import 'icon_action_button.dart';

class SourcePanel extends ConsumerWidget {
  const SourcePanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final settings = ref.watch(settingsProvider);
    final session = ref.read(workspaceProvider.notifier);

    return MockupCard(
      padding: const EdgeInsets.symmetric(
        horizontal: MockupLayout.space,
        vertical: MockupLayout.space,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            height: MockupLayout.panelHeaderH,
            child: Row(
              children: [
                const Spacer(),
                IconActionButton(
                  icon: Icons.open_in_full,
                  tooltip: l10n.expandPanel,
                  filled: false,
                  onPressed: () => session.toggleExpand('source'),
                ),
                const SizedBox(width: MockupLayout.headerControlsGap),
                AnimatedBuilder(
                  animation: session.sourceController,
                  builder: (context, _) {
                    return Text(
                      l10n.charCount(session.sourceController.text.length),
                      style: TextStyle(
                        fontSize: TranslatorPalette.fontSizeUi,
                        color: palette.textMuted,
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: MockupLayout.tabRowMargin),
          const SizedBox(height: MockupLayout.tabRowH),
          const SizedBox(height: MockupLayout.tabRowMargin),
          Expanded(
            child: MockupTextInset(
              key: const Key('source-editor'),
              controller: session.sourceController,
              scrollController: session.sourceScroll,
              style: editorTextStyle(settings, palette),
              hint: l10n.sourcePlaceholder,
              readOnly: false,
            ),
          ),
          const SizedBox(height: MockupLayout.space),
          Row(
            children: [
              MockupButton(
                variant: MockupButtonVariant.ghost,
                label: l10n.paste,
                onPressed: session.pasteSource,
              ),
              const SizedBox(width: MockupLayout.zoneGap),
              MockupButton(
                variant: MockupButtonVariant.ghost,
                label: l10n.clear,
                onPressed: session.clearSource,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
