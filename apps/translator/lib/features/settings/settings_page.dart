import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:translator_core/translator_core.dart';

import '../../core/app_log.dart';
import '../../core/theme/mockup_controls.dart';
import '../../l10n/app_localizations.dart';
import '../../platform/llm_key_store.dart';
import '../../platform/hotkey_parse.dart';
import '../../platform/window_shell.dart';
import '../../providers.dart';
import '../boot/init_error_screen.dart';
import '../session/workspace_controller.dart';
import 'model_picker_dialog.dart';
import 'settings_actions.dart';
import 'settings_draft.dart';
import 'settings_widgets.dart';

/// Полноэкранные настройки: черновик, живой preview темы, ОК / Применить / Отмена.
enum SettingsSection {
  appearance,
  translation,
  llm,
  files,
  argos,
  behavior,
  about,
}

enum ArgosLinkStatus { available, noModels, offline }

class SettingsPage extends ConsumerStatefulWidget {
  const SettingsPage({super.key});

  @override
  ConsumerState<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends ConsumerState<SettingsPage> {
  late AppSettings _snapshot;
  late AppSettings _draft;
  late final _FieldControllers _fields;
  var _section = SettingsSection.appearance;
  var _advanced = false;
  var _busy = false;
  String? _banner;
  var _bannerError = false;
  VoidCallback? _bannerRetry;
  String? _packagesDir;
  var _argosStatus = ArgosLinkStatus.offline;

  @override
  void initState() {
    super.initState();
    _snapshot = ref.read(settingsProvider);
    _draft = clampAppSettings(_snapshot.copyWith());
    _fields = _FieldControllers(_draft);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_hydrateApiKey());
      unawaited(_refreshArgosInfo());
    });
  }

  @override
  void dispose() {
    _fields.dispose();
    super.dispose();
  }

  Future<void> _hydrateApiKey() async {
    final provider = _draft.llm.provider;
    if (provider == 'local') {
      return;
    }
    final fromJson = _draft.llm.apiKeys[provider] ?? '';
    if (fromJson.isNotEmpty) {
      _fields.apiKey.text = fromJson;
      return;
    }
    try {
      final value = await ref.read(llmKeyStoreProvider).read(provider);
      if (mounted && _fields.apiKey.text.isEmpty) {
        _fields.apiKey.text = value;
      }
    } catch (e, st) {
      AppLog.warning('llm key read failed', e, st);
    }
  }

  void _setDraft(AppSettings next) {
    final appearancePreview = next.window.theme != _draft.window.theme ||
        next.window.opacity != _draft.window.opacity;
    setState(() => _draft = next);
    if (appearancePreview) {
      _previewAppearance(next);
    }
  }

  void _previewAppearance(AppSettings next) {
    final committed = ref.read(settingsProvider);
    if (committed.window.theme != next.window.theme ||
        committed.window.opacity != next.window.opacity) {
      ref.read(settingsProvider.notifier).replaceLocal(
            committed.copyWith(
              window: committed.window.copyWith(
                theme: next.window.theme,
                opacity: next.window.opacity,
              ),
            ),
          );
    }
    if (!inFlutterTest() && committed.window.opacity != next.window.opacity) {
      unawaited(WindowShell.setOpacity(next.window.opacity));
    }
  }

  AppSettings _collect() {
    final llm = _draft.llm;
    final keys = Map<String, String>.from(llm.apiKeys);
    if (llm.provider != 'local') {
      keys[llm.provider] = _fields.apiKey.text;
    }
    final urls = Map<String, String>.from(llm.providerUrls);
    urls[llm.provider] = _fields.baseUrl.text.trim();

    return clampAppSettings(
      _draft.copyWith(
        debounceMs: parseIntField(_fields.debounce.text, _draft.debounceMs),
        llmDebounceMs:
            parseIntField(_fields.llmDebounce.text, _draft.llmDebounceMs),
        llm: llm.copyWith(
          baseUrl: _fields.baseUrl.text.trim(),
          providerUrls: urls,
          apiKeys: keys,
          model: _fields.model.text.trim(),
          temperature: parseDoubleField(
            _fields.temperature.text,
            llm.temperature,
          ),
          maxTokens: parseIntField(_fields.maxTokens.text, llm.maxTokens),
          timeoutSec: parseIntField(_fields.timeoutSec.text, llm.timeoutSec),
          systemPrompt: _fields.systemPrompt.text,
          chunkMaxChars:
              parseIntField(_fields.chunkMaxChars.text, llm.chunkMaxChars),
          fileChunkMaxChars: parseIntField(
            _fields.fileChunkMaxChars.text,
            llm.fileChunkMaxChars,
          ),
        ),
        files: _draft.files.copyWith(
          outputSuffix: _fields.suffix.text.trim().isEmpty
              ? '_translated'
              : _fields.suffix.text.trim(),
          maxFileSizeMb: parseIntField(
            _fields.maxFileMb.text,
            _draft.files.maxFileSizeMb,
          ),
          hotkeyAutoTranslateMaxChars: parseIntField(
            _fields.hotkeyMax.text,
            _draft.files.hotkeyAutoTranslateMaxChars,
          ),
          largeFileWarnChars: parseIntField(
            _fields.largeWarn.text,
            _draft.files.largeFileWarnChars,
          ),
        ),
        behavior: _draft.behavior.copyWith(
          globalHotkey: _fields.hotkey.text.trim(),
          translationCacheSize: parseIntField(
            _fields.cacheSize.text,
            _draft.behavior.translationCacheSize,
          ),
        ),
      ),
    );
  }

  Future<AppSettings> _persistable(AppSettings next) async {
    final store = ref.read(llmKeyStoreProvider);
    var keepPlaintext = false;
    for (final provider in const ['openrouter', 'custom']) {
      final value = next.llm.apiKeys[provider] ?? '';
      final ok = await store.write(provider, value);
      if (!ok && value.trim().isNotEmpty) {
        keepPlaintext = true;
      }
    }
    if (keepPlaintext) {
      AppLog.warning(
        'secure storage unavailable, llm keys stay in settings for this session',
      );
      return next;
    }
    return settingsWithoutPlaintextKeys(
      next,
      editedProvider: next.llm.provider,
    );
  }

  Future<void> _apply() async {
    final l10n = AppLocalizations.of(context);
    var next = _collect();
    final hotkeyRaw = _fields.hotkey.text.trim();
    final hotkeyRejected =
        hotkeyRaw.isNotEmpty && parseGlobalHotkey(hotkeyRaw) == null;
    if (hotkeyRejected) {
      next = next.copyWith(
        behavior: next.behavior.copyWith(globalHotkey: ''),
      );
    }
    final persistable = await _persistable(next);
    final argosChanged =
        persistable.argos.packagesDir != _snapshot.argos.packagesDir ||
            persistable.argos.preferApiOverCli !=
                _snapshot.argos.preferApiOverCli ||
            persistable.argos.bundleModelsOnStart !=
                _snapshot.argos.bundleModelsOnStart;
    await ref.read(settingsProvider.notifier).update(persistable);
    if (!inFlutterTest()) {
      unawaited(WindowShell.setOpacity(persistable.window.opacity));
    }
    if (argosChanged) {
      unawaited(ref.read(workspaceProvider.notifier).refreshSidecar());
    }
    if (!mounted) {
      return;
    }
    setState(() {
      _snapshot = persistable;
      _draft = persistable.copyWith(
        llm: persistable.llm.copyWith(apiKeys: next.llm.apiKeys),
      );
      _fields.syncFrom(_draft);
      if (hotkeyRejected) {
        _banner = l10n.settingsHotkeyInvalid;
        _bannerError = true;
        _bannerRetry = null;
      }
    });
  }

  Future<void> _ok() async {
    await _apply();
    if (mounted) {
      Navigator.of(context).pop();
    }
  }

  void _cancel() {
    ref.read(settingsProvider.notifier).replaceLocal(_snapshot);
    if (!inFlutterTest()) {
      unawaited(WindowShell.setOpacity(_snapshot.window.opacity));
    }
    Navigator.of(context).pop();
  }

  void _showBanner(String message, {required bool error, VoidCallback? retry}) {
    setState(() {
      _banner = message;
      _bannerError = error;
      _bannerRetry = retry;
    });
  }

  void _clearBanner() {
    setState(() {
      _banner = null;
      _bannerRetry = null;
    });
  }

  Future<void> _refreshArgosInfo() async {
    final client = ref.read(sidecarClientProvider);
    if (client == null) {
      if (mounted) {
        setState(() {
          _argosStatus = ArgosLinkStatus.offline;
          _packagesDir = _draft.argos.packagesDir.isEmpty
              ? null
              : _draft.argos.packagesDir;
        });
      }
      return;
    }
    try {
      final models = await client.listModels();
      if (!mounted) {
        return;
      }
      final hasPairs = models.pairs.isNotEmpty;
      setState(() {
        _packagesDir =
            (models.packagesDir == null || models.packagesDir!.isEmpty)
                ? _draft.argos.packagesDir
                : models.packagesDir;
        _argosStatus =
            hasPairs ? ArgosLinkStatus.available : ArgosLinkStatus.noModels;
      });
      return;
    } catch (_) {
      // ниже health
    }
    try {
      final health = await client.getAuthenticatedHealth();
      if (!mounted) {
        return;
      }
      final hasPairs = health.pairs.isNotEmpty || health.argos == true;
      setState(() {
        _packagesDir =
            (health.packagesDir == null || health.packagesDir!.isEmpty)
                ? _draft.argos.packagesDir
                : health.packagesDir;
        if (!health.ok) {
          _argosStatus = ArgosLinkStatus.offline;
        } else {
          _argosStatus =
              hasPairs ? ArgosLinkStatus.available : ArgosLinkStatus.noModels;
        }
      });
    } catch (_) {
      if (mounted) {
        setState(() => _argosStatus = ArgosLinkStatus.offline);
      }
    }
  }

  LlmSettings _checkSettings() {
    final collected = _collect();
    return collected.llm;
  }

  Future<void> _checkConnection({required bool openPicker}) async {
    final l10n = AppLocalizations.of(context);
    var llm = _checkSettings();
    if (!llm.enabled) {
      _showBanner(l10n.settingsEnableLlmFirst, error: false);
      return;
    }
    setState(() => _busy = true);
    try {
      llm = await ref.read(llmKeyStoreProvider).attach(llm);
      final models = await ref.read(llmClientProvider).fetchModels(
            llm,
            timeout: Duration(seconds: llm.timeoutSec.clamp(5, 60).toInt()),
          );
      if (!mounted) {
        return;
      }
      if (openPicker) {
        if (models.isEmpty) {
          _showBanner(l10n.settingsLlmModelsEmpty, error: false);
          return;
        }
        if (mounted) {
          setState(() => _busy = false);
        }
        final picked = await showModelPickerDialog(
          context: context,
          models: models,
          selected: _fields.model.text,
        );
        if (picked != null && mounted) {
          _fields.model.text = picked;
          _setDraft(_draft.copyWith(llm: _draft.llm.copyWith(model: picked)));
        }
        _clearBanner();
      } else {
        _showBanner(l10n.settingsLlmConnected, error: false);
      }
    } on LlmDisabledException {
      if (mounted) {
        _showBanner(l10n.settingsEnableLlmFirst, error: false);
      }
    } catch (e) {
      if (mounted) {
        _showBanner(
          l10n.settingsLlmCheckFailed('$e'),
          error: true,
          retry: () => unawaited(_checkConnection(openPicker: openPicker)),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _installBundle() async {
    final l10n = AppLocalizations.of(context);
    final client = ref.read(sidecarClientProvider);
    if (client == null) {
      _showBanner(l10n.noTranslationEngine, error: true);
      return;
    }
    setState(() => _busy = true);
    try {
      final result = await client.installModels(bundle: true);
      await ref.read(workspaceProvider.notifier).refreshSidecar();
      await _refreshArgosInfo();
      if (mounted) {
        _showBanner(l10n.settingsModelsInstalled(result.installed),
            error: false);
      }
    } catch (e) {
      if (mounted) {
        _showBanner(
          l10n.installFailed,
          error: true,
          retry: () => unawaited(_installBundle()),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _installArgosModelFile() async {
    final l10n = AppLocalizations.of(context);
    if (inFlutterTest()) {
      return;
    }
    final client = ref.read(sidecarClientProvider);
    if (client == null) {
      _showBanner(l10n.noTranslationEngine, error: true);
      return;
    }
    final picked = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['argosmodel'],
    );
    final path = picked?.files.single.path;
    if (path == null || path.isEmpty) {
      return;
    }
    setState(() => _busy = true);
    try {
      final result = await client.installModels(path: path);
      await ref.read(workspaceProvider.notifier).refreshSidecar();
      await _refreshArgosInfo();
      if (mounted) {
        _showBanner(l10n.settingsModelsInstalled(result.installed),
            error: false);
      }
    } catch (e) {
      if (mounted) {
        _showBanner(l10n.installFailed, error: true);
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  void _setProvider(String provider) {
    final llm = _draft.llm;
    final urls = Map<String, String>.from(llm.providerUrls);
    urls[llm.provider] = _fields.baseUrl.text.trim();
    final nextUrl = urls[provider] ?? '';
    _fields.baseUrl.text = nextUrl;
    _fields.apiKey.text = llm.apiKeys[provider] ?? '';
    _setDraft(
      _draft.copyWith(
        llm: llm.copyWith(
          provider: provider,
          baseUrl: nextUrl,
          providerUrls: urls,
        ),
      ),
    );
    unawaited(_fillApiKeyFromStore(provider));
  }

  Future<void> _fillApiKeyFromStore(String provider) async {
    if (provider == 'local') {
      _fields.apiKey.text = '';
      return;
    }
    if (_fields.apiKey.text.isNotEmpty) {
      return;
    }
    try {
      final value = await ref.read(llmKeyStoreProvider).read(provider);
      if (mounted &&
          _draft.llm.provider == provider &&
          _fields.apiKey.text.isEmpty) {
        _fields.apiKey.text = value;
      }
    } catch (e, st) {
      AppLog.warning('llm key read failed', e, st);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette =
        TranslatorPalette.forBrightness(Theme.of(context).brightness);

    return CallbackShortcuts(
      bindings: {
        const SingleActivator(LogicalKeyboardKey.escape): _cancel,
      },
      child: Focus(
        autofocus: true,
        child: PopScope(
          canPop: false,
          onPopInvokedWithResult: (didPop, _) {
            if (!didPop) {
              _cancel();
            }
          },
          child: Scaffold(
            backgroundColor: palette.background,
            body: Align(
              alignment: Alignment.topCenter,
              child: ConstrainedBox(
                constraints:
                    const BoxConstraints(maxWidth: MockupLayout.settingsMaxW),
                child: Padding(
                  padding: const EdgeInsets.all(MockupLayout.space),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Padding(
                        padding:
                            const EdgeInsets.only(bottom: MockupLayout.space),
                        child: Text(
                          l10n.settingsTitle,
                          style: const TextStyle(
                            fontSize: TranslatorPalette.fontSizeTitle,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      if (_banner != null)
                        SettingsBanner(
                          key: const Key('settings-banner'),
                          message: _banner!,
                          isError: _bannerError,
                          retryLabel: l10n.retry,
                          closeLabel: l10n.clear,
                          onRetry: _bannerRetry,
                          onClose: _clearBanner,
                        ),
                      Expanded(
                        child: MockupCard(
                          padding: const EdgeInsets.all(MockupLayout.space),
                          child: ConstrainedBox(
                            constraints: const BoxConstraints(
                              minHeight: MockupLayout.settingsBodyMinH,
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                SizedBox(
                                  width: MockupLayout.settingsSidebarW,
                                  child: DecoratedBox(
                                    decoration: BoxDecoration(
                                      color: palette.backgroundElevated,
                                      borderRadius: BorderRadius.circular(
                                        TranslatorPalette.radiusControl,
                                      ),
                                      border: Border.all(color: palette.border),
                                    ),
                                    child: Padding(
                                      padding: const EdgeInsets.all(
                                        MockupLayout.settingsSidebarPad,
                                      ),
                                      child: ListView(
                                        children: [
                                          for (final section
                                              in SettingsSection.values)
                                            SettingsNavButton(
                                              key: Key(
                                                'settings-nav-${section.name}',
                                              ),
                                              label:
                                                  _sectionLabel(l10n, section),
                                              selected: _section == section,
                                              onPressed: () => setState(
                                                  () => _section = section),
                                            ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: MockupLayout.space),
                                Expanded(
                                  child: Stack(
                                    children: [
                                      Positioned.fill(
                                        child: SingleChildScrollView(
                                          padding: const EdgeInsets.all(
                                            MockupLayout.space,
                                          ),
                                          child: _buildSection(l10n, palette),
                                        ),
                                      ),
                                      if (_busy)
                                        const Positioned.fill(
                                          child: ColoredBox(
                                            color: Color(0x73000000),
                                            child: Center(
                                              child:
                                                  CircularProgressIndicator(),
                                            ),
                                          ),
                                        ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.only(top: MockupLayout.space),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            MockupButton(
                              key: const Key('settings-ok'),
                              variant: MockupButtonVariant.primary,
                              label: l10n.settingsOk,
                              onPressed: _busy ? null : () => unawaited(_ok()),
                            ),
                            const SizedBox(width: MockupLayout.space),
                            MockupButton(
                              key: const Key('settings-apply'),
                              variant: MockupButtonVariant.accent,
                              label: l10n.settingsApply,
                              onPressed:
                                  _busy ? null : () => unawaited(_apply()),
                            ),
                            const SizedBox(width: MockupLayout.space),
                            MockupButton(
                              key: const Key('settings-cancel'),
                              variant: MockupButtonVariant.accent,
                              label: l10n.settingsCancel,
                              onPressed: _busy ? null : _cancel,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  String _sectionLabel(AppLocalizations l10n, SettingsSection section) {
    return switch (section) {
      SettingsSection.appearance => l10n.settingsSectionAppearance,
      SettingsSection.translation => l10n.settingsSectionTranslation,
      SettingsSection.llm => l10n.settingsSectionLlm,
      SettingsSection.files => l10n.settingsSectionFiles,
      SettingsSection.argos => l10n.settingsSectionArgos,
      SettingsSection.behavior => l10n.settingsSectionBehavior,
      SettingsSection.about => l10n.settingsSectionAbout,
    };
  }

  Widget _buildSection(AppLocalizations l10n, TranslatorPalette palette) {
    return switch (_section) {
      SettingsSection.appearance => _appearance(l10n),
      SettingsSection.translation => _translation(l10n),
      SettingsSection.llm => _llm(l10n),
      SettingsSection.files => _files(l10n),
      SettingsSection.argos => _argos(l10n),
      SettingsSection.behavior => _behavior(l10n),
      SettingsSection.about => _about(l10n, palette),
    };
  }

  Widget _appearance(AppLocalizations l10n) {
    final fontPercent = (_draft.window.fontScale * 100).round();
    final opacityPercent = (_draft.window.opacity * 100).round();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SettingsIntro(text: l10n.settingsAppearanceIntro),
        SettingsFieldRow(
          label: l10n.settingsTheme,
          child: SettingsDropdown<String>(
            key: const Key('settings-theme'),
            value: _draft.window.theme == 'light' ? 'light' : 'dark',
            items: [
              ('dark', l10n.settingsThemeDark),
              ('light', l10n.settingsThemeLight),
            ],
            onChanged: (theme) => _setDraft(
              _draft.copyWith(window: _draft.window.copyWith(theme: theme)),
            ),
          ),
        ),
        SettingsFieldRow(
          label: l10n.settingsEditorFont,
          child: SettingsDropdown<String>(
            key: const Key('settings-editor-font'),
            value: _draft.window.editorFont == 'mono' ? 'mono' : 'system',
            items: [
              ('system', l10n.settingsFontSystem),
              ('mono', l10n.settingsFontMono),
            ],
            onChanged: (font) => _setDraft(
              _draft.copyWith(
                window: _draft.window.copyWith(editorFont: font),
              ),
            ),
          ),
        ),
        SettingsSliderRow(
          sliderKey: const Key('settings-font-scale'),
          label: l10n.settingsFontScale,
          value: fontPercent.toDouble().clamp(100, 200),
          min: 100,
          max: 200,
          display: '$fontPercent%',
          onChanged: (value) => _setDraft(
            _draft.copyWith(
              window: _draft.window.copyWith(fontScale: value / 100),
            ),
          ),
        ),
        SettingsSliderRow(
          sliderKey: const Key('settings-opacity'),
          label: l10n.settingsOpacity,
          value: opacityPercent.toDouble().clamp(30, 100),
          min: 30,
          max: 100,
          display: '$opacityPercent%',
          onChanged: (value) => _setDraft(
            _draft.copyWith(
              window: _draft.window.copyWith(opacity: value / 100),
            ),
          ),
        ),
      ],
    );
  }

  Widget _translation(AppLocalizations l10n) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SettingsIntro(text: l10n.settingsTranslationIntro),
        SettingsCheckbox(
          key: const Key('settings-streaming'),
          label: l10n.streamingToggle,
          value: _draft.streaming,
          onChanged: (value) => _setDraft(_draft.copyWith(streaming: value)),
        ),
        SettingsCheckbox(
          key: const Key('settings-scroll-sync'),
          label: l10n.settingsScrollSyncHonest,
          value: _draft.scrollSync,
          onChanged: (value) => _setDraft(_draft.copyWith(scrollSync: value)),
        ),
        SettingsFieldRow(
          label: l10n.settingsDebounceArgos,
          child: SettingsIntField(
            key: const Key('settings-debounce'),
            controller: _fields.debounce,
            onChanged: (raw) => _setDraft(
              _draft.copyWith(
                debounceMs: parseIntField(raw, _draft.debounceMs),
              ),
            ),
          ),
        ),
        SettingsFieldRow(
          label: l10n.settingsDebounceLlm,
          child: SettingsIntField(
            key: const Key('settings-llm-debounce'),
            controller: _fields.llmDebounce,
            onChanged: (raw) => _setDraft(
              _draft.copyWith(
                llmDebounceMs: parseIntField(raw, _draft.llmDebounceMs),
              ),
            ),
          ),
        ),
        SettingsCheckbox(
          key: const Key('settings-translation-cache'),
          label: l10n.settingsTranslationCache,
          value: _draft.behavior.translationCacheEnabled,
          onChanged: (value) => _setDraft(
            _draft.copyWith(
              behavior:
                  _draft.behavior.copyWith(translationCacheEnabled: value),
            ),
          ),
        ),
        if (_draft.behavior.translationCacheEnabled)
          SettingsFieldRow(
            label: l10n.settingsTranslationCacheSize,
            child: SettingsIntField(
              key: const Key('settings-cache-size'),
              controller: _fields.cacheSize,
              onChanged: (raw) => _setDraft(
                _draft.copyWith(
                  behavior: _draft.behavior.copyWith(
                    translationCacheSize: parseIntField(
                      raw,
                      _draft.behavior.translationCacheSize,
                    ),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _llm(AppLocalizations l10n) {
    final local = _draft.llm.provider == 'local';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SettingsIntro(text: l10n.settingsLlmIntro),
        SettingsCheckbox(
          key: const Key('settings-llm-enabled'),
          label: l10n.settingsLlmEnabled,
          value: _draft.llm.enabled,
          onChanged: (value) => _setDraft(
            _draft.copyWith(llm: _draft.llm.copyWith(enabled: value)),
          ),
        ),
        SettingsFieldRow(
          label: l10n.settingsLlmProvider,
          child: SettingsDropdown<String>(
            key: const Key('settings-llm-provider'),
            value: _draft.llm.provider,
            items: const [
              ('local', 'LOCAL'),
              ('openrouter', 'OpenRouter'),
              ('custom', 'Custom'),
            ],
            onChanged: _setProvider,
          ),
        ),
        SettingsFieldRow(
          label: l10n.settingsServerUrl,
          child: MockupTextField(
            key: const Key('settings-llm-url'),
            controller: _fields.baseUrl,
            hint: l10n.settingsServerUrlHint,
            onChanged: (value) {
              final urls = Map<String, String>.from(_draft.llm.providerUrls);
              urls[_draft.llm.provider] = value.trim();
              _setDraft(
                _draft.copyWith(
                  llm: _draft.llm
                      .copyWith(baseUrl: value.trim(), providerUrls: urls),
                ),
              );
            },
          ),
        ),
        SettingsFieldRow(
          label: l10n.settingsApiKey,
          child: MockupTextField(
            key: const Key('settings-llm-key'),
            controller: _fields.apiKey,
            enabled: !local,
            obscureText: true,
            onChanged: (value) {
              if (local) {
                return;
              }
              final keys = Map<String, String>.from(_draft.llm.apiKeys);
              keys[_draft.llm.provider] = value;
              _setDraft(
                _draft.copyWith(llm: _draft.llm.copyWith(apiKeys: keys)),
              );
            },
          ),
        ),
        if (local) SettingsMuted(text: l10n.settingsApiKeyLocalHint),
        if (_draft.llm.provider == 'openrouter')
          SettingsMuted(text: l10n.settingsLlmCloudWarning, warning: true),
        SettingsFieldRow(
          label: l10n.settingsLlmModel,
          child: MockupTextField(
            key: const Key('settings-llm-model'),
            controller: _fields.model,
            hint: l10n.settingsLlmModelHint,
            onChanged: (value) => _setDraft(
              _draft.copyWith(llm: _draft.llm.copyWith(model: value.trim())),
            ),
          ),
        ),
        SettingsActionColumn(
          children: [
            MockupButton(
              key: const Key('settings-llm-check'),
              variant: MockupButtonVariant.accent,
              width: MockupLayout.btnAccentWideW,
              label: l10n.settingsLlmCheck,
              onPressed: _busy
                  ? null
                  : () => unawaited(_checkConnection(openPicker: false)),
            ),
            MockupButton(
              key: const Key('settings-llm-load-models'),
              variant: MockupButtonVariant.accent,
              width: MockupLayout.btnAccentWideW,
              label: l10n.settingsLlmLoadModels,
              onPressed: _busy
                  ? null
                  : () => unawaited(_checkConnection(openPicker: true)),
            ),
          ],
        ),
        const SizedBox(height: MockupLayout.space),
        SettingsCheckbox(
          key: const Key('settings-llm-advanced'),
          label: l10n.settingsLlmAdvanced,
          value: _advanced,
          onChanged: (value) => setState(() => _advanced = value),
        ),
        if (_advanced) ...[
          SettingsFieldRow(
            label: l10n.settingsLlmTemperature,
            child: MockupTextField(
              key: const Key('settings-llm-temperature'),
              controller: _fields.temperature,
            ),
          ),
          SettingsFieldRow(
            label: l10n.settingsLlmMaxTokens,
            child: SettingsIntField(controller: _fields.maxTokens),
          ),
          SettingsFieldRow(
            label: l10n.settingsLlmTimeout,
            child: SettingsIntField(controller: _fields.timeoutSec),
          ),
          SettingsCheckbox(
            label: l10n.settingsLlmStream,
            value: _draft.llm.stream,
            onChanged: (value) => _setDraft(
              _draft.copyWith(llm: _draft.llm.copyWith(stream: value)),
            ),
          ),
          SettingsFieldRow(
            label: l10n.settingsLlmSystemPrompt,
            child: MockupTextField(
              controller: _fields.systemPrompt,
              maxLines: 6,
              minLines: 3,
            ),
          ),
          SettingsFieldRow(
            label: l10n.settingsLlmChunkMax,
            child: SettingsIntField(controller: _fields.chunkMaxChars),
          ),
          SettingsFieldRow(
            label: l10n.settingsLlmFileChunkMax,
            child: SettingsIntField(controller: _fields.fileChunkMaxChars),
          ),
          SettingsCheckbox(
            label: l10n.settingsLlmFileChunkContext,
            value: _draft.llm.fileChunkContext,
            onChanged: (value) => _setDraft(
              _draft.copyWith(
                llm: _draft.llm.copyWith(fileChunkContext: value),
              ),
            ),
          ),
          SettingsFieldRow(
            label: l10n.settingsLlmAuthHeader,
            child: SettingsDropdown<String>(
              value: _draft.llm.authHeader,
              items: [
                ('auto', l10n.settingsAuthAuto),
                ('Bearer', l10n.settingsAuthBearer),
                ('api-key', l10n.settingsAuthApiKey),
              ],
              onChanged: (value) => _setDraft(
                _draft.copyWith(llm: _draft.llm.copyWith(authHeader: value)),
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _files(AppLocalizations l10n) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SettingsIntro(text: l10n.settingsFilesIntro),
        SettingsFieldRow(
          label: l10n.settingsOutputEncoding,
          child: SettingsDropdown<String>(
            key: const Key('settings-encoding'),
            value: _draft.files.outputEncoding,
            items: [
              ('same', l10n.settingsEncodingSame),
              ('utf-8', l10n.settingsEncodingUtf8),
              ('utf-8-sig', l10n.settingsEncodingUtf8Bom),
            ],
            onChanged: (value) => _setDraft(
              _draft.copyWith(
                files: _draft.files.copyWith(outputEncoding: value),
              ),
            ),
          ),
        ),
        SettingsFieldRow(
          label: l10n.settingsFileSuffix,
          child: MockupTextField(
            key: const Key('settings-suffix'),
            controller: _fields.suffix,
          ),
        ),
        SettingsFieldRow(
          label: l10n.settingsMaxFileMb,
          child: SettingsIntField(
            key: const Key('settings-max-file-mb'),
            controller: _fields.maxFileMb,
          ),
        ),
        SettingsFieldRow(
          label: l10n.settingsHotkeyAutoTranslate,
          child: SettingsIntField(
            key: const Key('settings-hotkey-max'),
            controller: _fields.hotkeyMax,
          ),
        ),
        SettingsFieldRow(
          label: l10n.settingsLargeFileWarn,
          child: SettingsIntField(
            key: const Key('settings-large-warn'),
            controller: _fields.largeWarn,
          ),
        ),
        SettingsCheckbox(
          key: const Key('settings-translate-code'),
          label: l10n.settingsTranslateCodeBlocks,
          value: _draft.files.translateCodeBlocks,
          onChanged: (value) => _setDraft(
            _draft.copyWith(
              files: _draft.files.copyWith(translateCodeBlocks: value),
            ),
          ),
        ),
      ],
    );
  }

  Widget _argos(AppLocalizations l10n) {
    final packages = (_packagesDir == null || _packagesDir!.isEmpty)
        ? l10n.settingsPackagesUnknown
        : _packagesDir!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SettingsIntro(text: l10n.settingsArgosIntro),
        SettingsCheckbox(
          key: const Key('settings-bundle-on-start'),
          label: l10n.settingsBundleOnStart,
          value: _draft.argos.bundleModelsOnStart,
          onChanged: (value) => _setDraft(
            _draft.copyWith(
              argos: _draft.argos.copyWith(bundleModelsOnStart: value),
            ),
          ),
        ),
        SettingsCheckbox(
          key: const Key('settings-prefer-api'),
          label: l10n.settingsPreferApi,
          value: _draft.argos.preferApiOverCli,
          onChanged: (value) => _setDraft(
            _draft.copyWith(
              argos: _draft.argos.copyWith(preferApiOverCli: value),
            ),
          ),
        ),
        SettingsMuted(text: '${l10n.settingsPackagesDir}\n$packages'),
        SettingsActionColumn(
          children: [
            MockupButton(
              key: const Key('settings-open-packages'),
              variant: MockupButtonVariant.accent,
              width: MockupLayout.btnAccentWideW,
              label: l10n.settingsOpenPackages,
              onPressed: (_packagesDir == null || _packagesDir!.isEmpty)
                  ? null
                  : () => unawaited(openDirectoryInExplorer(_packagesDir!)),
            ),
            MockupButton(
              variant: MockupButtonVariant.accent,
              width: MockupLayout.btnAccentWideW,
              label: l10n.settingsInstallBundle,
              onPressed: _busy ? null : () => unawaited(_installBundle()),
            ),
            MockupButton(
              variant: MockupButtonVariant.accent,
              width: MockupLayout.btnAccentWideW,
              label: l10n.settingsInstallArgosModel,
              onPressed:
                  _busy ? null : () => unawaited(_installArgosModelFile()),
            ),
          ],
        ),
        const SizedBox(height: MockupLayout.space),
        Align(
          alignment: Alignment.centerLeft,
          child: MockupButton(
            variant: MockupButtonVariant.ghost,
            label: l10n.settingsArgosCatalog,
            onPressed: () => unawaited(openExternalUrl(argosModelsCatalogUrl)),
          ),
        ),
      ],
    );
  }

  Widget _behavior(AppLocalizations l10n) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SettingsIntro(text: l10n.settingsBehaviorIntro),
        SettingsFieldRow(
          label: l10n.settingsCloseAction,
          child: SettingsDropdown<String>(
            key: const Key('settings-close-action'),
            value: _draft.behavior.closeAction == 'exit' ? 'exit' : 'tray',
            items: [
              ('tray', l10n.settingsCloseTray),
              ('exit', l10n.settingsCloseExit),
            ],
            onChanged: (value) => _setDraft(
              _draft.copyWith(
                behavior: _draft.behavior.copyWith(closeAction: value),
              ),
            ),
          ),
        ),
        SettingsFieldRow(
          label: l10n.settingsGlobalHotkey,
          child: MockupTextField(
            key: const Key('settings-hotkey'),
            controller: _fields.hotkey,
            hint: l10n.settingsHotkeyUnassigned,
          ),
        ),
        SettingsCheckbox(
          key: const Key('settings-start-minimized'),
          label: l10n.settingsStartMinimized,
          value: _draft.behavior.startMinimizedToTray,
          onChanged: (value) => _setDraft(
            _draft.copyWith(
              behavior: _draft.behavior.copyWith(startMinimizedToTray: value),
            ),
          ),
        ),
        SettingsCheckbox(
          key: const Key('settings-restore-clipboard'),
          label: l10n.settingsRestoreClipboard,
          value: _draft.behavior.restoreClipboardAfterCapture,
          onChanged: (value) => _setDraft(
            _draft.copyWith(
              behavior:
                  _draft.behavior.copyWith(restoreClipboardAfterCapture: value),
            ),
          ),
        ),
        SettingsCheckbox(
          key: const Key('settings-copy-hide'),
          label: l10n.settingsCopyHideTray,
          value: _draft.behavior.minimizeToTrayOnCopyHide,
          onChanged: (value) => _setDraft(
            _draft.copyWith(
              behavior:
                  _draft.behavior.copyWith(minimizeToTrayOnCopyHide: value),
            ),
          ),
        ),
        SettingsCheckbox(
          key: const Key('settings-triple-copy'),
          label: l10n.settingsTripleCopy,
          value: _draft.behavior.tripleCopyEnabled,
          onChanged: (value) => _setDraft(
            _draft.copyWith(
              behavior: _draft.behavior.copyWith(tripleCopyEnabled: value),
            ),
          ),
        ),
      ],
    );
  }

  Widget _about(AppLocalizations l10n, TranslatorPalette palette) {
    final argosLabel = switch (_argosStatus) {
      ArgosLinkStatus.available => l10n.settingsArgosAvailable,
      ArgosLinkStatus.noModels => l10n.settingsArgosNoModels,
      ArgosLinkStatus.offline => l10n.settingsArgosOffline,
    };
    final llmLabel =
        _draft.llm.enabled ? l10n.settingsLlmOn : l10n.settingsLlmOff;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SettingsIntro(text: l10n.settingsAboutIntro),
        Text(
          l10n.appTitle,
          style: const TextStyle(
            fontSize: TranslatorPalette.fontSizeUi,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: MockupLayout.space),
        Text(argosLabel),
        Text(llmLabel),
        const SizedBox(height: MockupLayout.space),
        Text(
          '${l10n.settingsPathLabel} ${ArgosPaths.settingsFile.path}',
          style: TextStyle(
            fontSize: TranslatorPalette.fontSizeUi,
            color: palette.textMuted,
          ),
        ),
        const SizedBox(height: MockupLayout.space),
        Align(
          alignment: Alignment.centerLeft,
          child: MockupButton(
            variant: MockupButtonVariant.accent,
            width: MockupLayout.btnAccentWideW,
            label: l10n.openLog,
            onPressed: openLogFolder,
          ),
        ),
      ],
    );
  }
}

class _FieldControllers {
  _FieldControllers(AppSettings settings)
      : debounce = TextEditingController(text: '${settings.debounceMs}'),
        llmDebounce = TextEditingController(text: '${settings.llmDebounceMs}'),
        cacheSize = TextEditingController(
          text: '${settings.behavior.translationCacheSize}',
        ),
        baseUrl = TextEditingController(text: settings.llm.baseUrl),
        apiKey = TextEditingController(
          text: settings.llm.apiKeys[settings.llm.provider] ?? '',
        ),
        model = TextEditingController(text: settings.llm.model),
        temperature =
            TextEditingController(text: '${settings.llm.temperature}'),
        maxTokens = TextEditingController(text: '${settings.llm.maxTokens}'),
        timeoutSec = TextEditingController(text: '${settings.llm.timeoutSec}'),
        systemPrompt = TextEditingController(text: settings.llm.systemPrompt),
        chunkMaxChars =
            TextEditingController(text: '${settings.llm.chunkMaxChars}'),
        fileChunkMaxChars =
            TextEditingController(text: '${settings.llm.fileChunkMaxChars}'),
        suffix = TextEditingController(text: settings.files.outputSuffix),
        maxFileMb =
            TextEditingController(text: '${settings.files.maxFileSizeMb}'),
        hotkeyMax = TextEditingController(
          text: '${settings.files.hotkeyAutoTranslateMaxChars}',
        ),
        largeWarn = TextEditingController(
          text: '${settings.files.largeFileWarnChars}',
        ),
        hotkey = TextEditingController(text: settings.behavior.globalHotkey);

  void syncFrom(AppSettings settings) {
    debounce.text = '${settings.debounceMs}';
    llmDebounce.text = '${settings.llmDebounceMs}';
    cacheSize.text = '${settings.behavior.translationCacheSize}';
    baseUrl.text = settings.llm.baseUrl;
    apiKey.text = settings.llm.apiKeys[settings.llm.provider] ?? '';
    model.text = settings.llm.model;
    temperature.text = '${settings.llm.temperature}';
    maxTokens.text = '${settings.llm.maxTokens}';
    timeoutSec.text = '${settings.llm.timeoutSec}';
    systemPrompt.text = settings.llm.systemPrompt;
    chunkMaxChars.text = '${settings.llm.chunkMaxChars}';
    fileChunkMaxChars.text = '${settings.llm.fileChunkMaxChars}';
    suffix.text = settings.files.outputSuffix;
    maxFileMb.text = '${settings.files.maxFileSizeMb}';
    hotkeyMax.text = '${settings.files.hotkeyAutoTranslateMaxChars}';
    largeWarn.text = '${settings.files.largeFileWarnChars}';
    hotkey.text = settings.behavior.globalHotkey;
  }

  final TextEditingController debounce;
  final TextEditingController llmDebounce;
  final TextEditingController cacheSize;
  final TextEditingController baseUrl;
  final TextEditingController apiKey;
  final TextEditingController model;
  final TextEditingController temperature;
  final TextEditingController maxTokens;
  final TextEditingController timeoutSec;
  final TextEditingController systemPrompt;
  final TextEditingController chunkMaxChars;
  final TextEditingController fileChunkMaxChars;
  final TextEditingController suffix;
  final TextEditingController maxFileMb;
  final TextEditingController hotkeyMax;
  final TextEditingController largeWarn;
  final TextEditingController hotkey;

  void dispose() {
    debounce.dispose();
    llmDebounce.dispose();
    cacheSize.dispose();
    baseUrl.dispose();
    apiKey.dispose();
    model.dispose();
    temperature.dispose();
    maxTokens.dispose();
    timeoutSec.dispose();
    systemPrompt.dispose();
    chunkMaxChars.dispose();
    fileChunkMaxChars.dispose();
    suffix.dispose();
    maxFileMb.dispose();
    hotkeyMax.dispose();
    largeWarn.dispose();
    hotkey.dispose();
  }
}
