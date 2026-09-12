import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/mockup_controls.dart';
import '../../l10n/app_localizations.dart';
import '../../providers.dart';
import '../session/workspace_controller.dart';
import '../session/workspace_state.dart';
import 'editor_style.dart';
import 'empty_state.dart';
import 'icon_action_button.dart';

class TranslationPanel extends ConsumerWidget {
  const TranslationPanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final settings = ref.watch(settingsProvider);
    final sessionState = ref.watch(workspaceProvider);
    final session = ref.read(workspaceProvider.notifier);
    final llmEnabled = settings.llm.enabled;
    final isArgos = sessionState.activeTab != 'llm';

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
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconActionButton(
                      icon: Icons.open_in_full,
                      tooltip: l10n.expandPanel,
                      filled: false,
                      onPressed: () => session.toggleExpand('translation'),
                    ),
                    const SizedBox(width: MockupLayout.headerControlsGap),
                    _StatusBadge(
                      status: sessionState.argosStatus,
                      idle: l10n.argosIdle,
                      busy: l10n.argosBusy,
                      done: l10n.argosDone,
                      error: l10n.argosError,
                    ),
                    const SizedBox(width: MockupLayout.headerControlsGap),
                    MockupCheckbox(
                      key: const Key('llm-enable'),
                      value: llmEnabled,
                      compact: true,
                      tooltip: l10n.settingsLlmEnabled,
                      onChanged: (value) => session.setLlmEnabled(value),
                    ),
                    const SizedBox(width: MockupLayout.headerControlsGap),
                    _StatusBadge(
                      status: sessionState.llmStatus,
                      idle: l10n.llmIdle,
                      busy: l10n.llmBusy,
                      done: l10n.llmDone,
                      error: l10n.llmError,
                    ),
                  ],
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: MockupLayout.tabRowMargin),
            child: SizedBox(
              height: MockupLayout.tabRowH,
              child: _EngineTabs(
                argosSelected: isArgos,
                onArgos: () => session.setActiveTab('argos'),
                onLlm: () => session.setActiveTab('llm'),
              ),
            ),
          ),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(TranslatorPalette.radiusControl),
              child: Stack(
                children: [
                  Positioned.fill(
                    child: IndexedStack(
                      index: isArgos ? 0 : 1,
                      children: [
                        _TranslationEditor(
                          controller: session.argosController,
                          scrollController: session.argosScroll,
                        ),
                        _TranslationEditor(
                          controller: session.llmController,
                          scrollController: session.llmScroll,
                        ),
                      ],
                    ),
                  ),
                  Positioned.fill(
                    child: _TranslationOverlay(isArgos: isArgos),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: MockupLayout.space),
          Row(
            children: [
              MockupButton(
                variant: MockupButtonVariant.ghost,
                label: l10n.copy,
                onPressed: session.copyTranslation,
              ),
              const SizedBox(width: MockupLayout.zoneGap),
              MockupButton(
                variant: MockupButtonVariant.ghost,
                label: l10n.clear,
                onPressed: session.clearTranslation,
              ),
              const SizedBox(width: MockupLayout.zoneGap),
              MockupButton(
                variant: MockupButtonVariant.ghost,
                label: l10n.copyAndHide,
                onPressed: session.copyAndHide,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TranslationEditor extends ConsumerWidget {
  const _TranslationEditor({
    required this.controller,
    required this.scrollController,
  });

  final TextEditingController controller;
  final ScrollController scrollController;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsProvider);
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    return MockupTextInset(
      controller: controller,
      scrollController: scrollController,
      style: editorTextStyle(settings, palette),
      readOnly: true,
    );
  }
}

class _TranslationOverlay extends ConsumerWidget {
  const _TranslationOverlay({required this.isArgos});

  final bool isArgos;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final session = ref.watch(workspaceProvider);
    final controller = ref.read(workspaceProvider.notifier);
    final busy = isArgos ? session.argosBusy : session.llmBusy;
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);

    if (isArgos && !session.hasArgosModels) {
      return ColoredBox(
        color: palette.input.withValues(alpha: 0.92),
        child: EmptyState(
          icon: Icons.extension_off,
          title: l10n.noArgosModels,
          subtitle: l10n.noArgosModelsHint,
          action: MockupButton(
            variant: MockupButtonVariant.primary,
            label: l10n.installModels,
            onPressed: session.installingModels ? null : controller.installBundle,
          ),
        ),
      );
    }

    return AnimatedBuilder(
      animation: Listenable.merge([
        controller.argosController,
        controller.llmController,
      ]),
      builder: (context, _) {
        final text = isArgos
            ? controller.argosController.text
            : controller.llmController.text;
        if (busy || text.isNotEmpty) {
          return const SizedBox.shrink();
        }
        return IgnorePointer(
          child: ColoredBox(
            color: palette.input,
            child: EmptyState(
              icon: Icons.translate,
              title: l10n.emptyTranslationHint,
            ),
          ),
        );
      },
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
    required this.status,
    required this.idle,
    required this.busy,
    required this.done,
    required this.error,
  });

  final EngineRunStatus status;
  final String idle;
  final String busy;
  final String done;
  final String error;

  @override
  Widget build(BuildContext context) {
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    late final Color color;
    late final String label;
    switch (status) {
      case EngineRunStatus.idle:
        color = palette.textMuted;
        label = idle;
      case EngineRunStatus.busy:
        color = palette.warning;
        label = busy;
      case EngineRunStatus.done:
        color = palette.success;
        label = done;
      case EngineRunStatus.error:
        color = palette.danger;
        label = error;
    }
    return Text(
      label,
      style: TextStyle(
        fontSize: TranslatorPalette.fontSizeUi,
        color: color,
      ),
    );
  }
}

class _EngineTabs extends StatelessWidget {
  const _EngineTabs({
    required this.argosSelected,
    required this.onArgos,
    required this.onLlm,
  });

  final bool argosSelected;
  final VoidCallback onArgos;
  final VoidCallback onLlm;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    return Semantics(
      container: true,
      label: l10n.engineTabs,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: palette.backgroundElevated,
          borderRadius: BorderRadius.circular(TranslatorPalette.radiusControl),
        ),
        child: Row(
          children: [
            Expanded(
              child: _SegButton(
                key: const Key('engine-argos'),
                label: l10n.engineArgos,
                selected: argosSelected,
                onPressed: onArgos,
              ),
            ),
            Expanded(
              child: _SegButton(
                key: const Key('engine-llm'),
                label: l10n.engineLlm,
                selected: !argosSelected,
                onPressed: onLlm,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SegButton extends StatelessWidget {
  const _SegButton({
    super.key,
    required this.label,
    required this.selected,
    required this.onPressed,
  });

  final String label;
  final bool selected;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    return Semantics(
      button: true,
      selected: selected,
      child: GestureDetector(
        onTap: onPressed,
        child: ColoredBox(
          color: selected ? palette.primary : palette.accent,
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                fontFamily: 'Segoe UI',
                fontSize: TranslatorPalette.fontSizeUi,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
                color: selected ? palette.primaryForeground : palette.textPrimary,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
