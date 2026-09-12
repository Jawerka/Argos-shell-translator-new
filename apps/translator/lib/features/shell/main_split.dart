import 'dart:async';
import 'dart:math';

import 'package:desktop_drop/desktop_drop.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/translator_theme.dart';
import '../../l10n/app_localizations.dart';
import '../../providers.dart';
import '../session/scroll_sync.dart';
import '../session/workspace_controller.dart';
import '../session/workspace_state.dart';
import 'hint_banner.dart';
import 'main_toolbar.dart';
import 'source_panel.dart';
import 'status_bar.dart';
import 'translation_panel.dart';

class MainSplit extends ConsumerStatefulWidget {
  const MainSplit({super.key});

  @override
  ConsumerState<MainSplit> createState() => _MainSplitState();
}

class _MainSplitState extends ConsumerState<MainSplit> {
  var _syncing = false;
  late final WorkspaceController _session;

  @override
  void initState() {
    super.initState();
    _session = ref.read(workspaceProvider.notifier);
    _session.sourceScroll.addListener(_onSourceScroll);
    _session.argosScroll.addListener(_onArgosScroll);
    _session.llmScroll.addListener(_onLlmScroll);
  }

  @override
  void dispose() {
    _session.sourceScroll.removeListener(_onSourceScroll);
    _session.argosScroll.removeListener(_onArgosScroll);
    _session.llmScroll.removeListener(_onLlmScroll);
    super.dispose();
  }

  void _onSourceScroll() {
    _sync(
      from: _session.sourceScroll,
      to: _session.activeTranslationScroll,
      sourceToDest: true,
    );
  }

  void _onArgosScroll() {
    if (_session.isArgosTab) {
      _sync(
        from: _session.argosScroll,
        to: _session.sourceScroll,
        sourceToDest: false,
      );
    }
  }

  void _onLlmScroll() {
    if (!_session.isArgosTab) {
      _sync(
        from: _session.llmScroll,
        to: _session.sourceScroll,
        sourceToDest: false,
      );
    }
  }

  void _sync({
    required ScrollController from,
    required ScrollController to,
    required bool sourceToDest,
  }) {
    if (_syncing) {
      return;
    }
    final settings = ref.read(settingsProvider);
    if (!settings.scrollSync || settings.window.editorLayout != 'split') {
      return;
    }
    if (!from.hasClients || !to.hasClients) {
      return;
    }
    final fromMax = from.position.maxScrollExtent;
    final toMax = to.position.maxScrollExtent;
    if (fromMax <= 0 && toMax <= 0) {
      return;
    }
    final ratio = from.offset / max(fromMax, 1);
    var destRatio = ratio;
    final session = ref.read(workspaceProvider);
    final useParagraphs =
        _session.isArgosTab && session.hasArgosParagraphAnchors;
    if (useParagraphs) {
      final srcStarts = _session.sourceParaStarts;
      final dstStarts = _session.destParaStarts;
      if (sourceToDest) {
        final para = paragraphIndexForRatio(
          srcStarts,
          max(1, _session.sourceController.text.length),
          ratio,
        );
        destRatio = ratioForParagraph(
          dstStarts,
          max(1, _session.argosController.text.length),
          para,
        );
      } else {
        final para = paragraphIndexForRatio(
          dstStarts,
          max(1, _session.argosController.text.length),
          ratio,
        );
        destRatio = ratioForParagraph(
          srcStarts,
          max(1, _session.sourceController.text.length),
          para,
        );
      }
    }
    _syncing = true;
    to.jumpTo((destRatio * toMax).clamp(0, toMax));
    _syncing = false;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette =
        TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final settings = ref.watch(settingsProvider);
    final session = ref.watch(workspaceProvider);
    final layout = settings.window.editorLayout;

    return CallbackShortcuts(
      bindings: <ShortcutActivator, VoidCallback>{
        const SingleActivator(LogicalKeyboardKey.enter, control: true):
            _session.translateNow,
        const SingleActivator(LogicalKeyboardKey.escape): _session.stop,
        const SingleActivator(LogicalKeyboardKey.keyO, control: true): () =>
            unawaited(_session.openFilePicker()),
        const SingleActivator(LogicalKeyboardKey.keyS, control: true): () =>
            unawaited(_session.saveTranslation()),
        const SingleActivator(LogicalKeyboardKey.keyS,
            control: true, shift: true): () => unawaited(_session.saveBoth()),
        const SingleActivator(LogicalKeyboardKey.comma, control: true): () =>
            openSettingsPage(context),
        const _AltShiftActivator(): () => unawaited(_session.swapLanguages()),
      },
      child: Focus(
        autofocus: true,
        child: DropTarget(
          onDragDone: (detail) {
            if (detail.files.isEmpty) {
              return;
            }
            final path = detail.files.first.path;
            if (path.isEmpty) {
              return;
            }
            unawaited(_session.openDroppedPath(path));
          },
          child: Semantics(
            container: true,
            label: l10n.appTitle,
            child: Scaffold(
              backgroundColor: palette.background,
              body: Padding(
                padding: const EdgeInsets.all(MockupLayout.space),
                child: Column(
                  children: [
                    const MainToolbar(),
                    HintBanner(
                      hint: session.hint,
                      retry: session.hintRetry,
                      onClose: _session.clearHint,
                      onRetry: () {
                        switch (session.hintRetry) {
                          case HintRetry.llm:
                            unawaited(_session.retryLlm());
                          case HintRetry.settings:
                            openSettingsPage(context);
                          case HintRetry.translate:
                            unawaited(_session.translateNow());
                          case HintRetry.none:
                            break;
                        }
                      },
                    ),
                    const SizedBox(height: MockupLayout.space),
                    Expanded(
                      child: Row(
                        children: [
                          if (layout != 'translation')
                            const Expanded(child: SourcePanel()),
                          if (layout == 'split')
                            const SizedBox(width: MockupLayout.space),
                          if (layout != 'source')
                            const Expanded(child: TranslationPanel()),
                        ],
                      ),
                    ),
                    const SizedBox(height: MockupLayout.space),
                    const StatusBar(),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _AltShiftActivator extends ShortcutActivator {
  const _AltShiftActivator();

  @override
  bool accepts(KeyEvent event, HardwareKeyboard state) {
    if (event is! KeyDownEvent) {
      return false;
    }
    final key = event.logicalKey;
    final isAlt = key == LogicalKeyboardKey.alt ||
        key == LogicalKeyboardKey.altLeft ||
        key == LogicalKeyboardKey.altRight;
    final isShift = key == LogicalKeyboardKey.shift ||
        key == LogicalKeyboardKey.shiftLeft ||
        key == LogicalKeyboardKey.shiftRight;
    if (!isAlt && !isShift) {
      return false;
    }
    return state.isAltPressed && state.isShiftPressed;
  }

  @override
  String debugDescribeKeys() => 'Alt+Shift';
}
