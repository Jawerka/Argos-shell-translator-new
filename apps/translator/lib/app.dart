import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:translator_core/translator_core.dart';

import 'core/app_log.dart';
import 'core/detect_log.dart';
import 'core/theme/translator_theme.dart';
import 'features/boot/init_error_screen.dart';
import 'features/onboarding/first_run_page.dart';
import 'features/session/workspace_controller.dart';
import 'features/shell/main_split.dart';
import 'l10n/app_localizations.dart';
import 'l10n/app_localizations_ru.dart';
import 'platform/desktop_shell.dart';
import 'platform/launch_visibility.dart';
import 'platform/global_hotkey.dart';
import 'platform/instance_agent.dart';
import 'platform/sidecar_process.dart';
import 'platform/triple_copy.dart';
import 'providers.dart';

bool get inWidgetTest =>
    !kIsWeb && Platform.environment.containsKey('FLUTTER_TEST');

class TranslatorApp extends ConsumerStatefulWidget {
  const TranslatorApp({
    super.key,
    this.skipDesktopShell = false,
    this.skipSidecar = false,
    this.sidecar,
    this.initialError,
  });

  final bool skipDesktopShell;
  final bool skipSidecar;
  final SidecarProcess? sidecar;
  final String? initialError;

  @override
  ConsumerState<TranslatorApp> createState() => _TranslatorAppState();
}

class _TranslatorAppState extends ConsumerState<TranslatorApp> {
  var _ready = false;
  String? _error;
  late final SidecarProcess _sidecar;
  final _navigatorKey = GlobalKey<NavigatorState>();

  @override
  void initState() {
    super.initState();
    _error = widget.initialError;
    _sidecar = widget.sidecar ??
        (widget.skipSidecar || inWidgetTest
            ? SidecarProcess.disabled()
            : SidecarProcess());
    if (_error != null) {
      return;
    }
    if (widget.skipSidecar || _sidecar.disabled || inWidgetTest) {
      _ready = true;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_afterFirstFrame());
    });
  }

  Future<void> _afterFirstFrame() async {
    final settings = ref.read(settingsProvider);
    final skipDesktop = widget.skipDesktopShell || inWidgetTest;

    if (!skipDesktop && DesktopShell.isSupported) {
      DesktopShell.instance.shouldHideToTray = () =>
          ref.read(settingsProvider).behavior.closeAction == 'tray';
      DesktopShell.instance.onBeforeExit = () async {
        await GlobalHotkeyService.instance.unregister();
        await TripleCopyService.instance.stop();
        await _sidecar.stop();
        await InstanceAgent.instance.stop();
        await DetectLog.close();
        await AppLog.close();
      };
      DesktopShell.instance.attachWindowListener();
      final showWindow = shouldShowWindowAtLaunch(
        startMinimizedToTray: settings.behavior.startMinimizedToTray,
        debugMode: kDebugMode,
      );
      AppLog.info(
        'launch visibility show=$showWindow '
        'startMinimized=${settings.behavior.startMinimizedToTray} '
        'debug=$kDebugMode',
      );
      if (showWindow) {
        await DesktopShell.instance.applyLaunchVisibility(showWindow: true);
      }
      Future<void>.delayed(const Duration(milliseconds: 800), () async {
        if (!mounted) {
          return;
        }
        final l10n = _resolveL10n();
        await DesktopShell.instance.initTray(
          show: l10n.trayShow,
          exit: l10n.trayExit,
          tooltip: l10n.appTitle,
        );
        final latest = ref.read(settingsProvider);
        final hide = shouldHideAfterTrayInit(
          startMinimizedToTray: latest.behavior.startMinimizedToTray,
          debugMode: kDebugMode,
          trayInitialized: DesktopShell.instance.trayInitialized,
        );
        if (hide) {
          await DesktopShell.instance.applyLaunchVisibility(showWindow: false);
        } else if (!showWindow) {
          AppLog.warning('Tray unavailable — showing window instead of hiding');
          await DesktopShell.instance.applyLaunchVisibility(showWindow: true);
        }
      });
    }

    if (_ready || _error != null) {
      if (_ready && !skipDesktop) {
        await _syncGlobalHotkey(settings);
        await _syncTripleCopy(settings);
      }
      return;
    }

    try {
      _sidecar.onRestarting = () {
        ref.read(workspaceProvider.notifier).markEngineRestarting();
        ref.read(sidecarClientProvider.notifier).state = null;
      };
      _sidecar.onSessionChanged = (session) {
        if (!mounted || session == null) {
          return;
        }
        ref.read(sidecarClientProvider.notifier).state = SidecarClient(
          baseUri: session.baseUri,
          token: session.token,
        );
        ref.read(workspaceProvider.notifier).markEngineReady();
      };
      _sidecar.onRestartFailed = (error) {
        AppLog.error('sidecar supervision failed', error);
        if (mounted) {
          setState(() => _error = error.toString());
        }
      };
      await _sidecar.start(packagesDir: settings.argos.packagesDir);
      final session = _sidecar.session;
      if (session != null && mounted) {
        ref.read(sidecarClientProvider.notifier).state = SidecarClient(
          baseUri: session.baseUri,
          token: session.token,
        );
      }
      if (!mounted) {
        return;
      }
      setState(() => _ready = true);
      await _syncGlobalHotkey(settings);
      await _syncTripleCopy(settings);
    } catch (e, st) {
      AppLog.error('Sidecar boot failed', e, st);
      if (!mounted) {
        return;
      }
      setState(() => _error = e.toString());
    }
  }

  AppLocalizations _resolveL10n() {
    final navContext = _navigatorKey.currentContext;
    if (navContext != null) {
      final found = Localizations.of<AppLocalizations>(
        navContext,
        AppLocalizations,
      );
      if (found != null) {
        return found;
      }
    }
    return AppLocalizationsRu();
  }

  Future<void> _syncGlobalHotkey(AppSettings settings) async {
    if (widget.skipDesktopShell || inWidgetTest || inFlutterTest()) {
      return;
    }
    GlobalHotkeyService.instance.onTriggered = () async {
      await ref.read(workspaceProvider.notifier).captureFromGlobalHotkey();
    };
    await GlobalHotkeyService.instance.sync(settings.behavior.globalHotkey);
  }

  Future<void> _syncTripleCopy(AppSettings settings) async {
    if (widget.skipDesktopShell || inWidgetTest || inFlutterTest()) {
      return;
    }
    TripleCopyService.instance.onTriggered = () {
      unawaited(ref.read(workspaceProvider.notifier).captureFromTripleCopy());
    };
    await TripleCopyService.instance.sync(
      enabled: settings.behavior.tripleCopyEnabled,
    );
  }

  Widget _home(AppSettings settings) {
    if (_error != null) {
      return InitErrorScreen(message: _error!);
    }
    if (!_ready) {
      return const _BootSplash();
    }
    final showWizard = shouldShowFirstRun(
      firstRunDone: settings.firstRunDone,
      skipSidecar: widget.skipSidecar,
      inWidgetTest: inWidgetTest,
      inFlutterTest: inFlutterTest(),
    );
    if (showWizard) {
      return const FirstRunWizard();
    }
    return const MainSplit();
  }

  @override
  Widget build(BuildContext context) {
    final settings = ref.watch(settingsProvider);
    final light = settings.theme == 'light';

    ref.listen<AppSettings>(settingsProvider, (prev, next) {
      if (prev?.behavior.globalHotkey != next.behavior.globalHotkey) {
        unawaited(_syncGlobalHotkey(next));
      }
      if (prev?.behavior.tripleCopyEnabled != next.behavior.tripleCopyEnabled) {
        unawaited(_syncTripleCopy(next));
      }
    });

    return MaterialApp(
      navigatorKey: _navigatorKey,
      title: 'Argos Translate',
      debugShowCheckedModeBanner: false,
      theme: TranslatorTheme.light(),
      darkTheme: TranslatorTheme.dark(),
      themeMode: light ? ThemeMode.light : ThemeMode.dark,
      locale: const Locale('ru'),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: _home(settings),
    );
  }
}

class _BootSplash extends StatelessWidget {
  const _BootSplash();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            Text(l10n.loading),
          ],
        ),
      ),
    );
  }
}
