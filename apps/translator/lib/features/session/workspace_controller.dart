import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:translator_core/translator_core.dart';

import '../../core/app_log.dart';
import '../../platform/desktop_shell.dart';
import '../../platform/window_shell.dart';
import '../../platform/selection_capture.dart';
import '../../providers.dart';
import '../settings/settings_actions.dart';
import 'argos_assembler.dart';
import 'document_files.dart';
import 'language_swap.dart';
import 'workspace_state.dart';

final workspaceProvider = NotifierProvider<WorkspaceController, WorkspaceState>(
  WorkspaceController.new,
);

class WorkspaceController extends Notifier<WorkspaceState> {
  final sourceController = TextEditingController();
  final argosController = TextEditingController();
  final llmController = TextEditingController();
  final sourceScroll = ScrollController();
  final argosScroll = ScrollController();
  final llmScroll = ScrollController();

  final _assembler = ArgosAssembler();
  List<int> sourceParaStarts = const <int>[0];
  List<int> destParaStarts = const <int>[0];

  Timer? _argosDebounce;
  Timer? _llmDebounce;
  Timer? _llmUiTimer;
  var _argosGen = 0;
  var _llmGen = 0;
  var _llmCancelled = false;
  var _suppressSource = false;
  var _llmBuffer = '';
  int? _argosJobId;
  var _disposed = false;
  var _bundleInstallAttempted = false;

  @override
  WorkspaceState build() {
    final settings = ref.read(settingsProvider);
    sourceController.addListener(_onSourceChanged);
    ref.onDispose(_disposeResources);
    Future<void>.microtask(refreshSidecar);
    ref.listen<SidecarClient?>(sidecarClientProvider, (prev, next) {
      unawaited(refreshSidecar());
    });

    final tab = settings.llm.enabled ? settings.activeTranslationTab : 'argos';
    return WorkspaceState(
      langFrom: settings.langFrom,
      langTo: settings.langTo,
      activeTab: tab == 'llm' ? 'llm' : 'argos',
      languages: Map<String, String>.from(defaultLanguageNames),
    );
  }

  void _disposeResources() {
    _disposed = true;
    _argosDebounce?.cancel();
    _llmDebounce?.cancel();
    _llmUiTimer?.cancel();
    sourceController.removeListener(_onSourceChanged);
    sourceController.dispose();
    argosController.dispose();
    llmController.dispose();
    sourceScroll.dispose();
    argosScroll.dispose();
    llmScroll.dispose();
  }

  bool get isArgosTab => state.activeTab != 'llm';

  ScrollController get activeTranslationScroll =>
      isArgosTab ? argosScroll : llmScroll;

  String get activeTranslationText =>
      isArgosTab ? argosController.text : llmController.text;

  void _onSourceChanged() {
    if (_suppressSource || _disposed) {
      return;
    }
    final settings = ref.read(settingsProvider);
    if (!settings.streaming) {
      return;
    }
    _scheduleDebounced();
  }

  void _scheduleDebounced() {
    final settings = ref.read(settingsProvider);
    _argosDebounce?.cancel();
    _argosDebounce = Timer(
      Duration(milliseconds: settings.debounceMs),
      () => unawaited(_runArgos()),
    );
    if (settings.llm.enabled) {
      _llmDebounce?.cancel();
      _llmDebounce = Timer(
        Duration(milliseconds: settings.llmDebounceMs),
        () => unawaited(_runLlm()),
      );
    }
  }

  Future<void> refreshSidecar() async {
    final client = ref.read(sidecarClientProvider);
    if (client == null || _disposed) {
      return;
    }
    var languages = Map<String, String>.from(defaultLanguageNames);
    var hasModels = state.hasArgosModels;
    try {
      final fetched = await client.languages();
      if (fetched.isNotEmpty) {
        languages = Map<String, String>.from(fetched);
      }
    } catch (e, st) {
      AppLog.warning('languages() failed', e, st);
    }
    try {
      final health = await client.getAuthenticatedHealth();
      hasModels = health.argos == true || health.pairs.isNotEmpty;
    } catch (e, st) {
      AppLog.warning('health refresh failed', e, st);
    }
    try {
      final models = await client.listModels();
      hasModels = hasModels || models.pairs.isNotEmpty;
      if (!hasModels) {
        hasModels = models.pairs.isNotEmpty;
      }
    } catch (e, st) {
      AppLog.warning('listModels failed', e, st);
    }
    if (_disposed) {
      return;
    }
    state = state.copyWith(languages: languages, hasArgosModels: hasModels);
    final settings = ref.read(settingsProvider);
    if (shouldInstallBundleOnStart(
          bundleModelsOnStart: settings.argos.bundleModelsOnStart,
          hasModels: hasModels,
          firstRunDone: settings.firstRunDone,
          alreadyAttempted: _bundleInstallAttempted,
        ) &&
        !inFlutterTest()) {
      _bundleInstallAttempted = true;
      unawaited(installBundle());
    }
  }

  Future<void> translateNow() async {
    _argosDebounce?.cancel();
    _llmDebounce?.cancel();
    final text = sourceController.text;
    if (text.trim().length < 2) {
      return;
    }
    if (state.hint == SessionHint.largeFile) {
      state = state.copyWith(hint: SessionHint.none, hintRetry: HintRetry.none);
    }
    final settings = ref.read(settingsProvider);
    final sidecar = ref.read(sidecarClientProvider);
    if (sidecar == null && !settings.llm.enabled) {
      state = state.copyWith(hint: SessionHint.noEngine);
      return;
    }
    unawaited(_runArgos());
    if (settings.llm.enabled) {
      unawaited(_runLlm());
    }
  }

  Future<void> stop() async {
    _argosDebounce?.cancel();
    _llmDebounce?.cancel();
    _llmUiTimer?.cancel();
    _argosGen++;
    _llmGen++;
    _llmCancelled = true;
    _flushLlmUi();
    final client = ref.read(sidecarClientProvider);
    if (client != null) {
      try {
        await client.cancel(jobId: _argosJobId);
      } catch (e, st) {
        AppLog.warning('cancel failed', e, st);
      }
    }
    if (_disposed) {
      return;
    }
    state = state.copyWith(
      argosBusy: false,
      llmBusy: false,
      argosStatus: argosController.text.isEmpty
          ? EngineRunStatus.idle
          : EngineRunStatus.done,
      llmStatus: llmController.text.isEmpty
          ? EngineRunStatus.idle
          : EngineRunStatus.done,
    );
  }

  Future<void> retryLlm() async {
    state = state.copyWith(
      hint: SessionHint.none,
      hintRetry: HintRetry.none,
      clearLlmError: true,
    );
    await _runLlm();
  }

  void clearHint() {
    state = state.copyWith(hint: SessionHint.none, hintRetry: HintRetry.none);
  }

  Future<void> setLangFrom(String code) async {
    state = state.copyWith(
      langFrom: code,
      clearDetected: code != 'auto',
    );
    final settings = ref.read(settingsProvider);
    await ref.read(settingsProvider.notifier).update(
          settings.copyWith(langFrom: code),
        );
  }

  Future<void> setLangTo(String code) async {
    state = state.copyWith(langTo: code);
    final settings = ref.read(settingsProvider);
    await ref.read(settingsProvider.notifier).update(
          settings.copyWith(langTo: code),
        );
  }

  Future<void> swapLanguages() async {
    final next = swapLanguagePair(
      langFrom: state.langFrom,
      langTo: state.langTo,
      detectedLang: state.detectedLang,
    );
    state = state.copyWith(langFrom: next.from, langTo: next.to);
    final settings = ref.read(settingsProvider);
    await ref.read(settingsProvider.notifier).update(
          settings.copyWith(langFrom: next.from, langTo: next.to),
        );
  }

  Future<void> setActiveTab(String tab) async {
    final settings = ref.read(settingsProvider);
    final resolved = tab == 'llm' ? 'llm' : 'argos';
    state = state.copyWith(activeTab: resolved);
    await ref.read(settingsProvider.notifier).update(
          settings.copyWith(activeTranslationTab: resolved),
        );
  }

  Future<void> setLlmEnabled(bool value) async {
    final settings = ref.read(settingsProvider);
    var tab = state.activeTab;
    if (!value) {
      tab = 'argos';
      state = state.copyWith(activeTab: 'argos');
    }
    await ref.read(settingsProvider.notifier).update(
          settings.copyWith(
            llm: settings.llm.copyWith(enabled: value),
            activeTranslationTab: tab,
          ),
        );
  }

  Future<void> toggleExpand(String panel) async {
    final settings = ref.read(settingsProvider);
    final current = settings.window.editorLayout;
    final next = current == panel ? 'split' : panel;
    await ref.read(settingsProvider.notifier).update(
          settings.copyWith(
            window: settings.window.copyWith(editorLayout: next),
          ),
        );
  }

  Future<void> setStreaming(bool value) async {
    final settings = ref.read(settingsProvider);
    await ref.read(settingsProvider.notifier).update(
          settings.copyWith(streaming: value),
        );
  }

  Future<void> setScrollSync(bool value) async {
    final settings = ref.read(settingsProvider);
    await ref.read(settingsProvider.notifier).update(
          settings.copyWith(scrollSync: value),
        );
  }

  Future<void> pasteSource() async {
    final data = await Clipboard.getData(Clipboard.kTextPlain);
    final text = data?.text;
    if (text == null || text.isEmpty) {
      return;
    }
    _suppressSource = true;
    sourceController.text = text;
    _suppressSource = false;
    if (ref.read(settingsProvider).streaming) {
      _scheduleDebounced();
    }
  }

  /// Глобальный хоткей: захват выделения → показать окно → вставить → перевести.
  Future<void> captureFromGlobalHotkey() async {
    final settings = ref.read(settingsProvider);
    final text = await captureSelectionText(
      restoreOriginal: settings.behavior.restoreClipboardAfterCapture,
    );
    if (text == null || text.isEmpty || _disposed) {
      return;
    }
    if (!inFlutterTest()) {
      await WindowShell.showAndFocus();
    }
    _suppressSource = true;
    sourceController.text = text;
    _suppressSource = false;
    final maxChars = settings.files.hotkeyAutoTranslateMaxChars;
    if (maxChars <= 0 || text.length <= maxChars) {
      await translateNow();
    } else if (settings.streaming) {
      _scheduleDebounced();
    }
  }

  void clearSource() {
    _suppressSource = true;
    sourceController.clear();
    _suppressSource = false;
    unawaited(stop());
    if (!_disposed) {
      state = state.copyWith(clearDetected: true);
    }
  }

  void clearTranslation() {
    if (isArgosTab) {
      argosController.clear();
      state = state.copyWith(
        argosStatus: EngineRunStatus.idle,
        clearArgosError: true,
        hasArgosParagraphAnchors: false,
      );
    } else {
      llmController.clear();
      _llmBuffer = '';
      state = state.copyWith(
        llmStatus: EngineRunStatus.idle,
        clearLlmError: true,
      );
    }
  }

  Future<void> copyTranslation() async {
    final text = activeTranslationText;
    if (text.isEmpty) {
      return;
    }
    await Clipboard.setData(ClipboardData(text: text));
    state = state.copyWith(hint: SessionHint.copied);
  }

  Future<void> copyAndHide() async {
    await copyTranslation();
    final settings = ref.read(settingsProvider);
    if (settings.behavior.minimizeToTrayOnCopyHide &&
        !inFlutterTest() &&
        DesktopShell.instance.trayInitialized) {
      await WindowShell.hideToTray();
    }
  }

  Future<void> openFilePicker() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: textFileExtensions,
    );
    final path = result?.files.single.path;
    if (path == null || path.isEmpty) {
      return;
    }
    await openPath(path);
  }

  Future<void> openDroppedPath(String path) async {
    if (!isOpenableDocument(path)) {
      state = state.copyWith(hint: SessionHint.unsupportedFile);
      return;
    }
    await openPath(path);
  }

  Future<void> openPath(String path) async {
    final client = ref.read(sidecarClientProvider);
    if (client == null) {
      state = state.copyWith(hint: SessionHint.noEngine);
      return;
    }
    final settings = ref.read(settingsProvider);
    try {
      final decoded = await client.decodeFile(
        path: path,
        maxSizeMb: settings.files.maxFileSizeMb,
      );
      _suppressSource = true;
      sourceController.text = decoded.text;
      _suppressSource = false;
      final large = exceedsLargeFileWarn(
        decoded.text.length,
        settings.files.largeFileWarnChars,
      );
      state = state.copyWith(
        documentPath: decoded.path,
        documentEncoding: decoded.encoding,
        documentFileType: decoded.fileType,
        hint: large ? SessionHint.largeFile : SessionHint.none,
        hintRetry: large ? HintRetry.translate : HintRetry.none,
      );
      if (large) {
        return;
      }
      await translateNow();
    } catch (e, st) {
      AppLog.warning('decodeFile failed', e, st);
      state = state.copyWith(hint: SessionHint.unsupportedFile);
    }
  }

  Future<void> saveTranslation() async {
    final text = activeTranslationText;
    if (text.isEmpty) {
      state = state.copyWith(hint: SessionHint.noTranslation);
      return;
    }
    final settings = ref.read(settingsProvider);
    final src = state.documentPath ?? 'translation.txt';
    final suggested = suggestedTranslationPath(
      src,
      suffix: settings.files.outputSuffix,
      engine: state.activeTab,
    );
    String? path;
    try {
      path = await FilePicker.platform.saveFile(
        fileName: p.basename(suggested),
        type: FileType.custom,
        allowedExtensions: textFileExtensions,
      );
    } catch (e, st) {
      AppLog.warning('save file picker failed', e, st);
      return;
    }
    if (path == null || path.isEmpty) {
      return;
    }
    try {
      await writeEncodedTextFile(
        path: path,
        content: text,
        encoding: resolveOutputEncoding(
          state.documentEncoding,
          settings.files.outputEncoding,
        ),
      );
      state = state.copyWith(hint: SessionHint.saved);
    } catch (e, st) {
      AppLog.warning('save translation failed', e, st);
    }
  }

  Future<void> saveBoth() async {
    final doc = state.documentPath;
    if (doc == null || doc.isEmpty) {
      state = state.copyWith(hint: SessionHint.openFileFirst);
      return;
    }
    final settings = ref.read(settingsProvider);
    final argosText = argosController.text;
    final llmText = llmController.text;
    if (argosText.isEmpty && llmText.isEmpty) {
      state = state.copyWith(hint: SessionHint.noTranslation);
      return;
    }
    try {
      final encoding = resolveOutputEncoding(
        state.documentEncoding,
        settings.files.outputEncoding,
      );
      if (argosText.isNotEmpty) {
        final argosPath = suggestedTranslationPath(
          doc,
          suffix: settings.files.outputSuffix,
          engine: 'argos',
        );
        await writeEncodedTextFile(
          path: argosPath,
          content: argosText,
          encoding: encoding,
        );
      }
      if (settings.llm.enabled && llmText.isNotEmpty) {
        final llmPath = suggestedTranslationPath(
          doc,
          suffix: settings.files.outputSuffix,
          engine: 'llm',
        );
        await writeEncodedTextFile(
          path: llmPath,
          content: llmText,
          encoding: encoding,
        );
      }
      state = state.copyWith(hint: SessionHint.saved);
    } catch (e, st) {
      AppLog.warning('save both failed', e, st);
    }
  }

  Future<void> installBundle() async {
    final client = ref.read(sidecarClientProvider);
    if (client == null) {
      state = state.copyWith(hint: SessionHint.noEngine);
      return;
    }
    state = state.copyWith(installingModels: true);
    try {
      await client.installModels(bundle: true);
      await refreshSidecar();
    } catch (e, st) {
      AppLog.warning('install models failed', e, st);
      state = state.copyWith(hint: SessionHint.installFailed);
    } finally {
      if (!_disposed) {
        state = state.copyWith(installingModels: false);
      }
    }
  }

  Future<void> _runArgos() async {
    final text = sourceController.text;
    if (text.trim().length < 2) {
      return;
    }
    final settings = ref.read(settingsProvider);
    final client = ref.read(sidecarClientProvider);
    if (client == null) {
      return;
    }
    if (!state.hasArgosModels) {
      state = state.copyWith(
        argosBusy: false,
        argosStatus: EngineRunStatus.error,
        argosError: 'no-models',
      );
      return;
    }

    final gen = ++_argosGen;
    _argosJobId = null;
    try {
      await client.cancel();
    } catch (_) {}

    sourceParaStarts = paragraphStartOffsets(text);
    _assembler.reset(0);
    if (state.langFrom == 'auto') {
      unawaited(_detectForChip(client, text, gen));
    }

    state = state.copyWith(
      argosBusy: true,
      argosStatus: EngineRunStatus.busy,
      argosDone: 0,
      argosTotal: 0,
      clearArgosError: true,
      hasArgosParagraphAnchors: false,
    );

    final request = TranslateRequest(
      text: text,
      fromCode: state.langFrom,
      toCode: state.langTo,
      preferApi: settings.argos.preferApiOverCli,
      translateCodeBlocks: settings.files.translateCodeBlocks,
      cache: settings.behavior.translationCacheEnabled,
      cacheSize: settings.behavior.translationCacheSize,
      packagesDir: settings.argos.packagesDir.isEmpty
          ? null
          : settings.argos.packagesDir,
    );

    try {
      await for (final event in client.translate(request)) {
        if (gen != _argosGen || _disposed) {
          return;
        }
        _handleArgosEvent(event);
      }
    } catch (e, st) {
      AppLog.warning('Argos translate failed', e, st);
      if (gen != _argosGen || _disposed) {
        return;
      }
      state = state.copyWith(
        argosBusy: false,
        argosStatus: EngineRunStatus.error,
        argosError: e.toString(),
      );
    }
  }

  Future<void> _detectForChip(
    SidecarClient client,
    String text,
    int gen,
  ) async {
    try {
      final result = await client.detect(text);
      if (_disposed || gen != _argosGen) {
        return;
      }
      final code = result.code;
      if (code.isNotEmpty && code != 'auto') {
        state = state.copyWith(detectedLang: code);
      }
    } catch (e, st) {
      AppLog.warning('detect failed', e, st);
    }
  }

  void _handleArgosEvent(TranslateEvent event) {
    switch (event) {
      case TranslateStart():
        _argosJobId = event.jobId;
        _assembler.reset(event.unitCount);
        if (state.langFrom == 'auto' &&
            event.fromCode.isNotEmpty &&
            event.fromCode != 'auto') {
          state = state.copyWith(
            detectedLang: event.fromCode,
            argosBusy: true,
            argosStatus: EngineRunStatus.busy,
            argosTotal: event.unitCount,
            argosDone: 0,
          );
        } else {
          state = state.copyWith(
            argosBusy: true,
            argosStatus: EngineRunStatus.busy,
            argosTotal: event.unitCount,
            argosDone: 0,
          );
        }
      case TranslateChunk():
        _assembler.put(
          index: event.index,
          paraIdx: event.paraIdx,
          text: event.text,
        );
        _setArgosText(_assembler.assemble());
        destParaStarts = paragraphStartOffsets(argosController.text);
        state = state.copyWith(
          argosDone: event.done,
          argosTotal: event.total,
          hasArgosParagraphAnchors: _assembler.hasParagraphAnchors,
        );
      case TranslateDone():
        _setArgosText(_assembler.assemble());
        destParaStarts = paragraphStartOffsets(argosController.text);
        state = state.copyWith(
          argosBusy: false,
          argosStatus: EngineRunStatus.done,
          hasArgosParagraphAnchors: _assembler.hasParagraphAnchors,
        );
      case TranslateError():
        state = state.copyWith(
          argosBusy: false,
          argosStatus: EngineRunStatus.error,
          argosError: event.message,
        );
      case TranslateCancelled():
        state = state.copyWith(
          argosBusy: false,
          argosStatus: argosController.text.isEmpty
              ? EngineRunStatus.idle
              : EngineRunStatus.done,
        );
    }
  }

  void _setArgosText(String text) {
    final offset = argosScroll.hasClients ? argosScroll.offset : 0.0;
    argosController.value = TextEditingValue(
      text: text,
      selection: TextSelection.collapsed(offset: text.length),
    );
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!argosScroll.hasClients) {
        return;
      }
      final maxExtent = argosScroll.position.maxScrollExtent;
      argosScroll.jumpTo(offset.clamp(0, maxExtent));
    });
  }

  Future<void> _runLlm() async {
    final settings = ref.read(settingsProvider);
    if (!settings.llm.enabled) {
      return;
    }
    final text = sourceController.text;
    if (text.trim().length < 2) {
      return;
    }

    final llm = await ref.read(llmKeyStoreProvider).attach(settings.llm);
    final cfgErr = llmConfigError(llm);
    if (cfgErr != null) {
      state = state.copyWith(
        llmBusy: false,
        llmStatus: EngineRunStatus.error,
        llmReachable: false,
        hint: SessionHint.llmNotConfigured,
        hintRetry: HintRetry.settings,
      );
      return;
    }

    final gen = ++_llmGen;
    _llmCancelled = false;
    _llmBuffer = '';
    _llmUiTimer?.cancel();
    llmController.clear();

    state = state.copyWith(
      llmBusy: true,
      llmStatus: EngineRunStatus.busy,
      llmDone: 0,
      llmTotal: 0,
      clearLlmError: true,
    );

    final client = ref.read(llmClientProvider);
    final languages = state.languages.isNotEmpty
        ? state.languages
        : Map<String, String>.from(defaultLanguageNames);

    try {
      await for (final token in client.translate(
        settings: llm,
        text: text,
        fromCode: state.langFrom == 'auto'
            ? (state.detectedLang ?? 'auto')
            : state.langFrom,
        toCode: state.langTo,
        languages: languages,
        fileType: state.documentFileType,
        isCancelled: () => _llmCancelled || gen != _llmGen,
        onChunkProgress: (done, total) {
          if (gen != _llmGen || _disposed) {
            return;
          }
          state = state.copyWith(llmDone: done, llmTotal: total);
        },
      )) {
        if (gen != _llmGen || _disposed) {
          return;
        }
        _llmBuffer = token;
        _llmUiTimer ??= Timer(const Duration(milliseconds: 50), _flushLlmUi);
      }
      _flushLlmUi();
      if (gen != _llmGen || _disposed) {
        return;
      }
      state = state.copyWith(
        llmBusy: false,
        llmStatus: EngineRunStatus.done,
        llmReachable: true,
      );
    } on LlmCancelledException {
      if (gen != _llmGen || _disposed) {
        return;
      }
      _flushLlmUi();
      state = state.copyWith(
        llmBusy: false,
        llmStatus: llmController.text.isEmpty
            ? EngineRunStatus.idle
            : EngineRunStatus.done,
      );
    } on LlmConfigException {
      if (gen != _llmGen || _disposed) {
        return;
      }
      state = state.copyWith(
        llmBusy: false,
        llmStatus: EngineRunStatus.error,
        llmReachable: false,
        hint: SessionHint.llmNotConfigured,
        hintRetry: HintRetry.settings,
      );
    } catch (e, st) {
      AppLog.warning('LLM translate failed', e, st);
      if (gen != _llmGen || _disposed) {
        return;
      }
      _flushLlmUi();
      state = state.copyWith(
        llmBusy: false,
        llmStatus: EngineRunStatus.error,
        llmReachable: false,
        llmError: e.toString(),
        hint: SessionHint.llmConnection,
        hintRetry: HintRetry.llm,
      );
    }
  }

  void _flushLlmUi() {
    _llmUiTimer?.cancel();
    _llmUiTimer = null;
    llmController.value = TextEditingValue(
      text: _llmBuffer,
      selection: TextSelection.collapsed(offset: _llmBuffer.length),
    );
  }
}
