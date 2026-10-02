import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:translator_core/translator_core.dart';

import '../../core/app_log.dart';
import '../../core/detect_log.dart';
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
  var _lastSourceText = '';
  String? _pairCacheText;
  Future<({String from, String to, String detected})>? _pairFuture;

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
    if (_disposed) {
      return;
    }
    final text = sourceController.text;
    if (text == _lastSourceText) {
      return;
    }
    final replaced = sourceTextReplaced(_lastSourceText, text);
    _lastSourceText = text;
    _pairCacheText = null;
    _pairFuture = null;
    if (replaced && (state.pairOverride || state.pairPinned)) {
      state = state.copyWith(clearPairOverride: true, pairPinned: false);
    }
    if (_suppressSource) {
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
    var pairs = List<String>.from(state.argosPairs);
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
      if (health.pairs.isNotEmpty) {
        pairs = _pairStrings(health.pairs);
      }
    } catch (e, st) {
      AppLog.warning('health refresh failed', e, st);
    }
    try {
      final models = await client.listModels();
      hasModels = hasModels || models.pairs.isNotEmpty;
      if (models.pairs.isNotEmpty) {
        pairs = _pairStrings(models.pairs);
      }
    } catch (e, st) {
      AppLog.warning('listModels failed', e, st);
    }
    if (_disposed) {
      return;
    }
    state = state.copyWith(
      languages: languages,
      hasArgosModels: hasModels,
      argosPairs: pairs,
    );
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
    ref.read(llmClientProvider).abort();
    final client = ref.read(sidecarClientProvider);
    if (client != null) {
      client.abortInFlight();
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
      clearPairOverride: true,
      pairPinned: code != 'auto',
    );
    _pairCacheText = null;
    _pairFuture = null;
    final settings = ref.read(settingsProvider);
    await ref.read(settingsProvider.notifier).update(
          settings.copyWith(langFrom: code),
        );
  }

  Future<void> setLangTo(String code) async {
    state = state.copyWith(
      langTo: code,
      pairPinned: state.langFrom != 'auto',
    );
    _pairCacheText = null;
    _pairFuture = null;
    final settings = ref.read(settingsProvider);
    await ref.read(settingsProvider.notifier).update(
          settings.copyWith(langTo: code, autoTargetLang: code),
        );
  }

  Future<void> swapLanguages() async {
    final peek = peekWords(sourceController.text);
    if (state.langFrom == 'auto') {
      if (state.pairOverride) {
        final oldFrom = state.overrideFrom ?? '';
        final oldTo = state.overrideTo ?? '';
        state = state.copyWith(clearPairOverride: true);
        _pairCacheText = null;
        _pairFuture = null;
        DetectLog.info(
          'fn=swap reason=override_clear peek="$peek" '
          'from=$oldFrom→$oldTo to=auto',
        );
        await translateNow();
        return;
      }
      final current = await _resolvePair(sourceController.text);
      state = state.copyWith(
        pairOverride: true,
        overrideFrom: current.to,
        overrideTo: current.from,
        detectedLang: current.to,
        resolvedTo: current.from,
      );
      _pairCacheText = null;
      _pairFuture = null;
      DetectLog.info(
        'fn=swap reason=override peek="$peek" '
        'from=${current.from}→${current.to} to=${current.to}→${current.from}',
      );
      await translateNow();
      return;
    }

    final next = swapLanguagePair(
      langFrom: state.langFrom,
      langTo: state.langTo,
    );
    final oldFrom = state.langFrom;
    final oldTo = state.langTo;
    state = state.copyWith(
      langFrom: next.from,
      langTo: next.to,
      pairPinned: true,
      clearPairOverride: true,
    );
    _pairCacheText = null;
    _pairFuture = null;
    DetectLog.info(
      'fn=swap reason=explicit peek="$peek" '
      'from=$oldFrom→$oldTo to=${next.from}→${next.to}',
    );
    final settings = ref.read(settingsProvider);
    await ref.read(settingsProvider.notifier).update(
          settings.copyWith(
            langFrom: next.from,
            langTo: next.to,
            autoTargetLang: next.to,
          ),
        );
    await translateNow();
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

  /// Тройной Ctrl+C: текст уже в буфере, SendInput не нужен.
  Future<void> captureFromTripleCopy({int? sequenceChanged}) async {
    if (sequenceChanged != null && sequenceChanged <= 0) {
      return;
    }
    final data = await Clipboard.getData(Clipboard.kTextPlain);
    final text = data?.text?.trim();
    if (text == null || text.isEmpty || _disposed) {
      return;
    }
    if (!inFlutterTest()) {
      await WindowShell.showAndFocus();
    }
    _suppressSource = true;
    sourceController.text = text;
    _suppressSource = false;
    final settings = ref.read(settingsProvider);
    final maxChars = settings.files.hotkeyAutoTranslateMaxChars;
    if (maxChars <= 0 || text.length <= maxChars) {
      await translateNow();
    } else if (settings.streaming) {
      _scheduleDebounced();
    }
  }

  void markEngineRestarting() {
    if (_disposed) {
      return;
    }
    state = state.copyWith(hint: SessionHint.engineRestarting);
  }

  void markEngineReady() {
    if (_disposed) {
      return;
    }
    if (state.hint == SessionHint.engineRestarting) {
      state = state.copyWith(hint: SessionHint.none);
    }
  }

  void clearSource() {
    _suppressSource = true;
    sourceController.clear();
    _suppressSource = false;
    unawaited(stop());
    if (!_disposed) {
      state = state.copyWith(clearDetected: true, clearResolved: true);
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
    client.abortInFlight();
    try {
      await client.cancel();
    } catch (_) {}

    final pair = await _resolvePair(text);
    if (gen != _argosGen || _disposed) {
      return;
    }

    sourceParaStarts = paragraphStartOffsets(text);
    _assembler.reset(0);

    state = state.copyWith(
      argosBusy: true,
      argosStatus: EngineRunStatus.busy,
      argosDone: 0,
      argosTotal: 0,
      clearArgosError: true,
      hasArgosParagraphAnchors: false,
      detectedLang: pair.detected,
      resolvedTo: pair.to,
    );

    final request = TranslateRequest(
      text: text,
      fromCode: pair.from,
      toCode: pair.to,
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

  bool _explicitConflict(SourceVerdict verdict) {
    final from = state.langFrom.trim().toLowerCase();
    final to = state.langTo.trim().toLowerCase();
    if (from == 'auto') {
      return false;
    }
    const enRu = {'en', 'ru'};
    if (!enRu.contains(from) || !enRu.contains(to)) {
      return false;
    }
    final source = verdict.explicitSource;
    return source != null && source != from;
  }

  String _verdictLog(SourceVerdict verdict) {
    return 'cyr=${verdict.cyr} lat=${verdict.lat} other=${verdict.other} '
        'share=${verdict.share.toStringAsFixed(2)} auto=${verdict.auto}';
  }

  void _rememberLanguage(String code) {
    if (code.isEmpty || state.languages.containsKey(code)) {
      return;
    }
    final name = defaultLanguageNames[code] ?? code.toUpperCase();
    state = state.copyWith(
      languages: {...state.languages, code: name},
    );
  }

  Future<({String from, String to, String detected})> _resolvePair(
    String text,
  ) {
    final peek = peekWords(text);
    final verdict = sourceVerdict(text);
    final counts = _verdictLog(verdict);
    if (state.langFrom == 'auto' && state.pairOverride) {
      final from = (state.overrideFrom ?? state.langTo).trim();
      final to = (state.overrideTo ?? 'ru').trim();
      DetectLog.info(
        'fn=resolvePair reason=override peek="$peek" len=${text.length} '
        '$counts pair=$from→$to',
      );
      return Future.value((from: from, to: to, detected: from));
    }
    if (state.langFrom != 'auto') {
      if (state.pairPinned || !_explicitConflict(verdict)) {
        DetectLog.info(
          'fn=resolvePair reason=explicit peek="$peek" len=${text.length} '
          '$counts pair=${state.langFrom}→${state.langTo}',
        );
        return Future.value(
          (
            from: state.langFrom,
            to: state.langTo,
            detected: state.langFrom,
          ),
        );
      }
      return _correctExplicitPair(text, verdict);
    }
    final cacheHit = _pairCacheText == text && _pairFuture != null;
    DetectLog.info(
      'fn=resolvePair begin peek="$peek" len=${text.length} '
      'langFrom=auto $counts cache=${cacheHit ? "hit" : "miss"}',
    );
    if (cacheHit) {
      DetectLog.info('fn=resolvePair skip reason=cache peek="$peek"');
      return _pairFuture!;
    }
    _pairCacheText = text;
    _pairFuture = _detectAutoPair(text, verdict);
    return _pairFuture!;
  }

  Future<({String from, String to, String detected})> _correctExplicitPair(
    String text,
    SourceVerdict verdict,
  ) async {
    final peek = peekWords(text);
    final from = state.langTo;
    final to = state.langFrom;
    state = state.copyWith(
      langFrom: from,
      langTo: to,
      detectedLang: from,
      resolvedTo: to,
    );
    final settings = ref.read(settingsProvider);
    await ref.read(settingsProvider.notifier).update(
          settings.copyWith(langFrom: from, langTo: to, autoTargetLang: to),
        );
    DetectLog.info(
      'fn=resolvePair reason=correct peek="$peek" len=${text.length} '
      '${_verdictLog(verdict)} pair=$from→$to',
    );
    return (from: from, to: to, detected: from);
  }

  Future<({String from, String to, String detected})> _detectAutoPair(
    String text,
    SourceVerdict verdict,
  ) async {
    final peek = peekWords(text);
    late final ({String from, String to}) pair;
    var label = '-';
    if (verdict.auto == 'ru') {
      pair = (from: 'ru', to: 'en');
    } else {
      var lang = 'en';
      final client = ref.read(sidecarClientProvider);
      if (client == null) {
        DetectLog.info(
          'fn=detectAutoPair sidecar_skip reason=no_client peek="$peek"',
        );
      } else {
        DetectLog.info('fn=detectAutoPair sidecar_call peek="$peek"');
        try {
          final result = await client.detect(text);
          final tag = result.lang.trim().toLowerCase();
          DetectLog.info(
            'fn=detectAutoPair sidecar_ok code=${result.code} '
            'lang=$tag peek="$peek"',
          );
          if (tag.isNotEmpty && tag != 'auto' && tag != 'ru') {
            lang = tag;
          }
        } catch (e, st) {
          DetectLog.info(
            'fn=detectAutoPair sidecar_fail peek="$peek" err=$e',
          );
          AppLog.warning('detect failed', e, st);
        }
      }
      _rememberLanguage(lang);
      label = lang;
      pair = (from: lang, to: 'ru');
    }
    DetectLog.info(
      'fn=resolvePair reason=auto peek="$peek" ${_verdictLog(verdict)} '
      'label=$label pair=${pair.from}→${pair.to}',
    );
    if (!_disposed) {
      state = state.copyWith(detectedLang: pair.from, resolvedTo: pair.to);
    }
    return (from: pair.from, to: pair.to, detected: pair.from);
  }

  void _handleArgosEvent(TranslateEvent event) {
    switch (event) {
      case TranslateStart():
        _argosJobId = event.jobId;
        _assembler.reset(event.unitCount);
        state = state.copyWith(
          argosBusy: true,
          argosStatus: EngineRunStatus.busy,
          argosTotal: event.unitCount,
          argosDone: 0,
        );
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
        AppLog.warning(
          'Argos translate failed job_id=${event.jobId} ${event.message}',
        );
        state = state.copyWith(
          argosBusy: false,
          argosStatus: EngineRunStatus.error,
          argosError: event.message,
        );
      case TranslateCancelled():
        AppLog.info('Argos job cancelled job_id=${event.jobId}');
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
    ref.read(llmClientProvider).abort();

    final pair = await _resolvePair(text);
    if (gen != _llmGen || _disposed) {
      return;
    }

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
        fromCode: pair.from,
        toCode: pair.to,
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

List<String> _pairStrings(List<Object?> raw) {
  return [
    for (final item in raw)
      if (item != null && item.toString().trim().isNotEmpty)
        item.toString().trim(),
  ];
}
