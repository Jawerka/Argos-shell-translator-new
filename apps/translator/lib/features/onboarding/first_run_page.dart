import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:translator_core/translator_core.dart';

import '../../core/app_log.dart';
import '../../core/theme/mockup_controls.dart';
import '../../l10n/app_localizations.dart';
import '../../platform/llm_key_store.dart';
import '../../providers.dart';
import '../session/workspace_controller.dart';
import '../settings/settings_widgets.dart';

/// Мастер только для нового профиля, не в widget-тестах и не при skipSidecar.
bool shouldShowFirstRun({
  required bool firstRunDone,
  required bool skipSidecar,
  required bool inWidgetTest,
  required bool inFlutterTest,
}) {
  return !firstRunDone && !skipSidecar && !inWidgetTest && !inFlutterTest;
}

/// Первый запуск: тема → модели Argos → LLM → трей.
class FirstRunWizard extends ConsumerStatefulWidget {
  const FirstRunWizard({super.key, this.onDone});

  final VoidCallback? onDone;

  @override
  ConsumerState<FirstRunWizard> createState() => _FirstRunWizardState();
}

class _FirstRunWizardState extends ConsumerState<FirstRunWizard> {
  var _step = 0;
  var _busy = false;
  String? _error;
  late AppSettings _draft;
  late bool _llmEnabled;
  late String _llmProvider;
  late final TextEditingController _llmUrl;
  late final TextEditingController _llmKey;

  @override
  void initState() {
    super.initState();
    _draft = ref.read(settingsProvider);
    _llmEnabled = _draft.llm.enabled;
    _llmProvider = _draft.llm.provider;
    _llmUrl = TextEditingController(text: _safeUrl(_draft.llm.baseUrl));
    _llmKey = TextEditingController();
  }

  @override
  void dispose() {
    _llmUrl.dispose();
    _llmKey.dispose();
    super.dispose();
  }

  String _safeUrl(String raw) {
    if (raw.contains('192.168.88.41')) {
      return '';
    }
    return raw;
  }

  void _previewTheme(String theme) {
    setState(() {
      _draft = _draft.copyWith(window: _draft.window.copyWith(theme: theme));
    });
    final committed = ref.read(settingsProvider);
    ref.read(settingsProvider.notifier).replaceLocal(
          committed.copyWith(
            window: committed.window.copyWith(theme: theme),
          ),
        );
  }

  Future<void> _persistDraft() async {
    await ref.read(settingsProvider.notifier).update(_draft);
  }

  Future<void> _goNext() async {
    if (_step == 2) {
      _applyLlmFields();
    }
    await _persistDraft();
    if (!mounted) {
      return;
    }
    if (_step >= 3) {
      await _finish();
      return;
    }
    setState(() {
      _step++;
      _error = null;
    });
  }

  Future<void> _skip() async {
    await _persistDraft();
    if (!mounted) {
      return;
    }
    if (_step >= 3) {
      await _finish();
      return;
    }
    setState(() {
      _step++;
      _error = null;
    });
  }

  void _applyLlmFields() {
    final urls = Map<String, String>.from(_draft.llm.providerUrls);
    final url = _safeUrl(_llmUrl.text.trim());
    urls[_llmProvider] = url;
    _draft = _draft.copyWith(
      llm: _draft.llm.copyWith(
        enabled: _llmEnabled,
        provider: _llmProvider,
        baseUrl: url,
        providerUrls: urls,
      ),
    );
  }

  Future<void> _finish() async {
    final keyStore = ref.read(llmKeyStoreProvider);
    var llm = _draft.llm;
    if (llm.provider != 'local') {
      final keyValue = _llmKey.text;
      final ok = await keyStore.write(llm.provider, keyValue);
      if (ok) {
        llm = settingsWithoutPlaintextKeys(
          _draft.copyWith(
            llm: llm.copyWith(
              apiKeys: {
                ...llm.apiKeys,
                llm.provider: keyValue,
              },
            ),
          ),
          editedProvider: llm.provider,
        ).llm;
      } else if (keyValue.trim().isNotEmpty) {
        llm = llm.copyWith(
          apiKeys: {
            ...llm.apiKeys,
            llm.provider: keyValue,
          },
        );
        AppLog.warning(
          'secure storage unavailable, llm keys kept for this session',
        );
      }
    }
    await ref.read(settingsProvider.notifier).update(
          _draft.copyWith(llm: llm, firstRunDone: true),
        );
    widget.onDone?.call();
  }

  Future<void> _installBundle() async {
    final l10n = AppLocalizations.of(context);
    final client = ref.read(sidecarClientProvider);
    if (client == null) {
      setState(() => _error = l10n.noTranslationEngine);
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await client.installModels(bundle: true);
      await ref.read(workspaceProvider.notifier).refreshSidecar();
      if (!mounted) {
        return;
      }
      await _goNext();
    } catch (e, st) {
      AppLog.warning('first-run install models failed', e, st);
      if (mounted) {
        setState(() => _error = l10n.installFailed);
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  void _setLlmProvider(String provider) {
    final urls = Map<String, String>.from(_draft.llm.providerUrls);
    urls[_llmProvider] = _safeUrl(_llmUrl.text.trim());
    final nextUrl = _safeUrl(urls[provider] ?? '');
    setState(() {
      _llmProvider = provider;
      _llmUrl.text = nextUrl;
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);

    return Scaffold(
      backgroundColor: palette.background,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  minHeight: constraints.maxHeight - 32,
                  maxWidth: 560,
                ),
                child: Center(
                  child: MockupCard(
                    child: Padding(
                      padding: const EdgeInsets.all(MockupLayout.space),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            l10n.firstRunTitle,
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            l10n.firstRunSubtitle,
                            style:
                                Theme.of(context).textTheme.bodyMedium?.copyWith(
                                      color: palette.textMuted,
                                    ),
                          ),
                          const SizedBox(height: 16),
                          _buildStep(l10n),
                          if (_error != null) ...[
                            const SizedBox(height: 12),
                            Text(
                              _error!,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(
                                    color: palette.danger,
                                  ),
                            ),
                          ],
                          if (_busy) ...[
                            const SizedBox(height: 12),
                            const Center(child: CircularProgressIndicator()),
                          ],
                          const SizedBox(height: 16),
                          _actions(l10n),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildStep(AppLocalizations l10n) {
    return switch (_step) {
      0 => _themeStep(l10n),
      1 => _modelsStep(l10n),
      2 => _llmStep(l10n),
      _ => _trayStep(l10n),
    };
  }

  Widget _choiceRow({
    required String groupValue,
    required List<(String, String, Key)> items,
    required ValueChanged<String> onSelected,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final item in items) ...[
          Semantics(
            button: true,
            selected: groupValue == item.$1,
            label: item.$2,
            child: groupValue == item.$1
                ? MockupButton(
                    key: item.$3,
                    variant: MockupButtonVariant.primary,
                    label: item.$2,
                    expand: true,
                    alignStart: true,
                    onPressed: () => onSelected(item.$1),
                  )
                : MockupButton(
                    key: item.$3,
                    variant: MockupButtonVariant.ghost,
                    label: item.$2,
                    expand: true,
                    alignStart: true,
                    onPressed: () => onSelected(item.$1),
                  ),
          ),
          const SizedBox(height: 8),
        ],
      ],
    );
  }

  Widget _themeStep(AppLocalizations l10n) {
    final theme = _draft.window.theme == 'light' ? 'light' : 'dark';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(l10n.firstRunStepTheme, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        _choiceRow(
          groupValue: theme,
          items: [
            ('dark', l10n.settingsThemeDark, const Key('first-run-theme-dark')),
            ('light', l10n.settingsThemeLight, const Key('first-run-theme-light')),
          ],
          onSelected: _previewTheme,
        ),
      ],
    );
  }

  Widget _modelsStep(AppLocalizations l10n) {
    final sidecarMissing = ref.read(sidecarClientProvider) == null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(l10n.firstRunStepModels, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        Text(l10n.firstRunModelsHint),
        if (sidecarMissing) ...[
          const SizedBox(height: 8),
          Text(
            l10n.noTranslationEngine,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: TranslatorPalette.forBrightness(
                    Theme.of(context).brightness,
                  ).danger,
                ),
          ),
        ],
        const SizedBox(height: 12),
        Semantics(
          button: true,
          label: l10n.settingsInstallBundle,
          child: MockupButton(
            key: const Key('first-run-install'),
            variant: MockupButtonVariant.accent,
            width: MockupLayout.btnAccentWideW,
            label: l10n.settingsInstallBundle,
            onPressed: _busy ? null : () => unawaited(_installBundle()),
          ),
        ),
      ],
    );
  }

  Widget _llmStep(AppLocalizations l10n) {
    final local = _llmProvider == 'local';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(l10n.firstRunStepLlm, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        SettingsCheckbox(
          key: const Key('first-run-llm-enabled'),
          label: l10n.settingsLlmEnabled,
          value: _llmEnabled,
          onChanged: (value) => setState(() => _llmEnabled = value),
        ),
        SettingsFieldRow(
          label: l10n.settingsLlmProvider,
          child: SettingsDropdown<String>(
            value: _llmProvider,
            items: const [
              ('local', 'LOCAL'),
              ('openrouter', 'OpenRouter'),
              ('custom', 'Custom'),
            ],
            onChanged: _setLlmProvider,
          ),
        ),
        SettingsFieldRow(
          label: l10n.settingsServerUrl,
          child: MockupTextField(
            key: const Key('first-run-llm-url'),
            controller: _llmUrl,
            hint: l10n.settingsServerUrlHint,
          ),
        ),
        if (!local)
          SettingsFieldRow(
            label: l10n.settingsApiKey,
            child: MockupTextField(
              controller: _llmKey,
              obscureText: true,
            ),
          ),
        if (_llmProvider == 'openrouter')
          SettingsMuted(text: l10n.settingsLlmCloudWarning, warning: true),
      ],
    );
  }

  Widget _trayStep(AppLocalizations l10n) {
    final action = _draft.behavior.closeAction == 'exit' ? 'exit' : 'tray';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(l10n.firstRunStepTray, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        _choiceRow(
          groupValue: action,
          items: [
            ('tray', l10n.settingsCloseTray, const Key('first-run-close-tray')),
            ('exit', l10n.settingsCloseExit, const Key('first-run-close-exit')),
          ],
          onSelected: (value) {
            setState(() {
              _draft = _draft.copyWith(
                behavior: _draft.behavior.copyWith(closeAction: value),
              );
            });
          },
        ),
      ],
    );
  }

  Widget _actions(AppLocalizations l10n) {
    final showSkip = _step == 1 || _step == 2;
    final showContinue = _step != 1;
    final isLast = _step >= 3;
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        if (showSkip)
          Semantics(
            button: true,
            label: l10n.firstRunSkip,
            child: MockupButton(
              key: const Key('first-run-skip'),
              variant: MockupButtonVariant.accent,
              label: l10n.firstRunSkip,
              onPressed: _busy ? null : () => unawaited(_skip()),
            ),
          ),
        if (showSkip && showContinue) const SizedBox(width: MockupLayout.space),
        if (showContinue)
          Semantics(
            button: true,
            label: isLast ? l10n.firstRunDone : l10n.firstRunContinue,
            child: MockupButton(
              key: isLast
                  ? const Key('first-run-finish')
                  : const Key('first-run-continue'),
              variant: MockupButtonVariant.primary,
              label: isLast ? l10n.firstRunDone : l10n.firstRunContinue,
              onPressed:
                  _busy ? null : () => unawaited(isLast ? _finish() : _goNext()),
            ),
          ),
      ],
    );
  }
}
