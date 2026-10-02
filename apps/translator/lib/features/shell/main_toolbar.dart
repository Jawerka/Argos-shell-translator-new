import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/mockup_controls.dart';
import '../../l10n/app_localizations.dart';
import '../../platform/desktop_shell.dart';
import '../../providers.dart';
import '../session/workspace_controller.dart';
import '../settings/settings_page.dart';
import 'icon_action_button.dart';

class MainToolbar extends ConsumerWidget {
  const MainToolbar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final settings = ref.watch(settingsProvider);
    final session = ref.read(workspaceProvider.notifier);

    return MockupCard(
      child: SizedBox(
        height: MockupLayout.toolbarH,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: MockupLayout.space,
            vertical: MockupLayout.space,
          ),
          child: Row(
            children: [
              _FileMenu(l10n: l10n, session: session),
              const SizedBox(width: MockupLayout.space),
              Expanded(
                child: _LanguageCenter(
                  l10n: l10n,
                  palette: palette,
                ),
              ),
              const SizedBox(width: MockupLayout.space),
              _MoreMenu(
                l10n: l10n,
                streaming: settings.streaming,
                scrollSync: settings.scrollSync,
              ),
              const SizedBox(width: MockupLayout.zoneGap),
              MockupButton(
                variant: MockupButtonVariant.primary,
                label: l10n.translate,
                onPressed: () => unawaited(session.translateNow()),
              ),
              const SizedBox(width: MockupLayout.zoneGap),
              MockupButton(
                variant: MockupButtonVariant.ghost,
                label: l10n.stop,
                onPressed: () => unawaited(session.stop()),
              ),
              const SizedBox(width: MockupLayout.zoneGap),
              IconActionButton(
                icon: Icons.settings,
                tooltip: l10n.settingsTitle,
                onPressed: () => openSettingsPage(context),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

void openSettingsPage(BuildContext context) {
  Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => const SettingsPage(),
    ),
  );
}

class _FileMenu extends StatelessWidget {
  const _FileMenu({required this.l10n, required this.session});

  final AppLocalizations l10n;
  final WorkspaceController session;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: l10n.fileMenu,
      child: PopupMenuButton<String>(
        tooltip: l10n.fileMenu,
        padding: EdgeInsets.zero,
        onSelected: (value) {
          switch (value) {
            case 'open':
              unawaited(session.openFilePicker());
            case 'save':
              unawaited(session.saveTranslation());
            case 'saveBoth':
              unawaited(session.saveBoth());
            case 'exit':
              if (!inFlutterTest()) {
                unawaited(DesktopShell.instance.shutdown());
              }
          }
        },
        itemBuilder: (context) => [
          PopupMenuItem(value: 'open', child: Text(l10n.fileOpen)),
          PopupMenuItem(value: 'save', child: Text(l10n.fileSaveTranslation)),
          PopupMenuItem(value: 'saveBoth', child: Text(l10n.fileSaveBoth)),
          const PopupMenuDivider(),
          PopupMenuItem(value: 'exit', child: Text(l10n.fileExit)),
        ],
        child: MockupButton.chrome(
          icon: Icons.description_outlined,
          tooltip: l10n.fileMenu,
          variant: MockupButtonVariant.accent,
        ),
      ),
    );
  }
}

class _MoreMenu extends ConsumerWidget {
  const _MoreMenu({
    required this.l10n,
    required this.streaming,
    required this.scrollSync,
  });

  final AppLocalizations l10n;
  final bool streaming;
  final bool scrollSync;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return PopupMenuButton<String>(
      tooltip: l10n.moreMenu,
      padding: EdgeInsets.zero,
      onSelected: (value) {
        final session = ref.read(workspaceProvider.notifier);
        switch (value) {
          case 'streaming':
            unawaited(session.setStreaming(!streaming));
          case 'scrollSync':
            unawaited(session.setScrollSync(!scrollSync));
        }
      },
      itemBuilder: (context) => [
        CheckedPopupMenuItem<String>(
          value: 'streaming',
          checked: streaming,
          child: Text(l10n.streamingToggle),
        ),
        CheckedPopupMenuItem<String>(
          value: 'scrollSync',
          checked: scrollSync,
          child: Text(l10n.scrollSyncToggle),
        ),
      ],
      child: MockupButton.chrome(
        label: l10n.moreMenu,
        variant: MockupButtonVariant.ghost,
      ),
    );
  }
}

class _LanguageCenter extends ConsumerWidget {
  const _LanguageCenter({required this.l10n, required this.palette});

  final AppLocalizations l10n;
  final TranslatorPalette palette;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sessionState = ref.watch(workspaceProvider);
    final session = ref.read(workspaceProvider.notifier);
    final languages = sessionState.languages;
    final codes = languages.keys.toList()..sort();
    final fromItems = <String>['auto', ...codes];
    if (!fromItems.contains(sessionState.langFrom)) {
      fromItems.add(sessionState.langFrom);
    }
    final toItems = List<String>.from(codes);
    if (toItems.isEmpty) {
      toItems.addAll(['en', 'ru']);
    }
    if (!toItems.contains(sessionState.langTo)) {
      toItems.add(sessionState.langTo);
    }

    final detected = sessionState.detectedLang;
    final resolvedTo = sessionState.resolvedTo ?? sessionState.langTo;
    final showChip = sessionState.langFrom == 'auto' &&
        detected != null &&
        detected.isNotEmpty;
    final chipLabel = showChip
        ? '${detected.toUpperCase()} → ${resolvedTo.toUpperCase()}'
            '${sessionState.pairOverride ? ' ·' : ''}'
        : '';

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Flexible(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: MockupLayout.langComboMaxW),
            child: _LangDropdown(
              key: const Key('lang-from'),
              label: l10n.langFrom,
              value: sessionState.langFrom,
              items: fromItems,
              languages: languages,
              autoLabel: l10n.langAuto,
              onChanged: session.setLangFrom,
            ),
          ),
        ),
        if (showChip) ...[
          const SizedBox(width: MockupLayout.zoneGap),
          Tooltip(
            message: sessionState.pairOverride
                ? l10n.pairOverrideTooltip
                : l10n.detectedLangTooltip,
            child: Container(
              key: const Key('detected-lang'),
              height: MockupLayout.langComboH,
              padding: const EdgeInsets.symmetric(horizontal: MockupLayout.space),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: palette.accent,
                borderRadius: BorderRadius.circular(TranslatorPalette.radiusControl),
              ),
              child: Text(
                chipLabel,
                style: TextStyle(
                  fontSize: TranslatorPalette.fontSizeUi,
                  fontWeight: FontWeight.w700,
                  color: palette.textMuted,
                ),
              ),
            ),
          ),
        ],
        const SizedBox(width: MockupLayout.zoneGap),
        IconActionButton(
          icon: Icons.swap_horiz,
          tooltip: l10n.swapLanguages,
          onPressed: session.swapLanguages,
        ),
        const SizedBox(width: MockupLayout.zoneGap),
        Flexible(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: MockupLayout.langComboMaxW),
            child: _LangDropdown(
              key: const Key('lang-to'),
              label: l10n.langTo,
              value: sessionState.langTo,
              items: toItems,
              languages: languages,
              autoLabel: l10n.langAuto,
              onChanged: session.setLangTo,
            ),
          ),
        ),
      ],
    );
  }
}

class _LangDropdown extends StatelessWidget {
  const _LangDropdown({
    super.key,
    required this.label,
    required this.value,
    required this.items,
    required this.languages,
    required this.autoLabel,
    required this.onChanged,
  });

  final String label;
  final String value;
  final List<String> items;
  final Map<String, String> languages;
  final String autoLabel;
  final Future<void> Function(String code) onChanged;

  @override
  Widget build(BuildContext context) {
    return MockupSelect<String>(
      key: key,
      semanticLabel: label,
      height: MockupLayout.langComboH,
      value: items.contains(value) ? value : items.first,
      items: [
        for (final code in items) (code, _labelFor(code)),
      ],
      onChanged: (next) => unawaited(onChanged(next)),
    );
  }

  String _labelFor(String code) {
    if (code == 'auto') {
      return autoLabel;
    }
    final name = languages[code];
    if (name == null || name.isEmpty) {
      return code.toUpperCase();
    }
    return '${code.toUpperCase()} - $name';
  }
}
