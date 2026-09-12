enum EngineRunStatus { idle, busy, done, error }

enum SessionHint {
  none,
  llmNotConfigured,
  llmConnection,
  unsupportedFile,
  openFileFirst,
  saved,
  noEngine,
  noTranslation,
  installFailed,
  copied,
  largeFile,
  engineRestarting,
}

enum HintRetry { none, llm, settings, translate }

class WorkspaceState {
  const WorkspaceState({
    this.langFrom = 'auto',
    this.langTo = 'ru',
    this.detectedLang,
    this.resolvedTo,
    this.argosStatus = EngineRunStatus.idle,
    this.llmStatus = EngineRunStatus.idle,
    this.argosBusy = false,
    this.llmBusy = false,
    this.argosError,
    this.llmError,
    this.activeTab = 'argos',
    this.languages = const <String, String>{},
    this.hasArgosModels = true,
    this.argosPairs = const <String>[],
    this.llmReachable,
    this.documentPath,
    this.documentEncoding,
    this.documentFileType,
    this.argosDone = 0,
    this.argosTotal = 0,
    this.llmDone = 0,
    this.llmTotal = 0,
    this.installingModels = false,
    this.hint = SessionHint.none,
    this.hintRetry = HintRetry.none,
    this.hasArgosParagraphAnchors = false,
  });

  final String langFrom;
  final String langTo;
  final String? detectedLang;
  final String? resolvedTo;
  final EngineRunStatus argosStatus;
  final EngineRunStatus llmStatus;
  final bool argosBusy;
  final bool llmBusy;
  final String? argosError;
  final String? llmError;
  final String activeTab;
  final Map<String, String> languages;
  final bool hasArgosModels;
  final List<String> argosPairs;
  final bool? llmReachable;
  final String? documentPath;
  final String? documentEncoding;
  final String? documentFileType;
  final int argosDone;
  final int argosTotal;
  final int llmDone;
  final int llmTotal;
  final bool installingModels;
  final SessionHint hint;
  final HintRetry hintRetry;
  final bool hasArgosParagraphAnchors;

  bool get isBusy => argosBusy || llmBusy || installingModels;

  String? get visibleArgosError {
    final err = argosError;
    if (argosStatus != EngineRunStatus.error) {
      return null;
    }
    if (err == null || err.isEmpty || err == 'no-models') {
      return null;
    }
    return err;
  }

  WorkspaceState copyWith({
    String? langFrom,
    String? langTo,
    String? detectedLang,
    bool clearDetected = false,
    String? resolvedTo,
    bool clearResolved = false,
    EngineRunStatus? argosStatus,
    EngineRunStatus? llmStatus,
    bool? argosBusy,
    bool? llmBusy,
    String? argosError,
    bool clearArgosError = false,
    String? llmError,
    bool clearLlmError = false,
    String? activeTab,
    Map<String, String>? languages,
    bool? hasArgosModels,
    List<String>? argosPairs,
    bool? llmReachable,
    bool clearLlmReachable = false,
    String? documentPath,
    String? documentEncoding,
    String? documentFileType,
    int? argosDone,
    int? argosTotal,
    int? llmDone,
    int? llmTotal,
    bool? installingModels,
    SessionHint? hint,
    HintRetry? hintRetry,
    bool? hasArgosParagraphAnchors,
  }) {
    return WorkspaceState(
      langFrom: langFrom ?? this.langFrom,
      langTo: langTo ?? this.langTo,
      detectedLang: clearDetected ? null : (detectedLang ?? this.detectedLang),
      resolvedTo: clearResolved ? null : (resolvedTo ?? this.resolvedTo),
      argosStatus: argosStatus ?? this.argosStatus,
      llmStatus: llmStatus ?? this.llmStatus,
      argosBusy: argosBusy ?? this.argosBusy,
      llmBusy: llmBusy ?? this.llmBusy,
      argosError: clearArgosError ? null : (argosError ?? this.argosError),
      llmError: clearLlmError ? null : (llmError ?? this.llmError),
      activeTab: activeTab ?? this.activeTab,
      languages: languages ?? this.languages,
      hasArgosModels: hasArgosModels ?? this.hasArgosModels,
      argosPairs: argosPairs ?? this.argosPairs,
      llmReachable:
          clearLlmReachable ? null : (llmReachable ?? this.llmReachable),
      documentPath: documentPath ?? this.documentPath,
      documentEncoding: documentEncoding ?? this.documentEncoding,
      documentFileType: documentFileType ?? this.documentFileType,
      argosDone: argosDone ?? this.argosDone,
      argosTotal: argosTotal ?? this.argosTotal,
      llmDone: llmDone ?? this.llmDone,
      llmTotal: llmTotal ?? this.llmTotal,
      installingModels: installingModels ?? this.installingModels,
      hint: hint ?? this.hint,
      hintRetry: hintRetry ?? this.hintRetry,
      hasArgosParagraphAnchors:
          hasArgosParagraphAnchors ?? this.hasArgosParagraphAnchors,
    );
  }
}
