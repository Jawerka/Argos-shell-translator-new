import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:tray_manager/tray_manager.dart';
import 'package:window_manager/window_manager.dart';

import '../core/app_log.dart';
import 'launch_visibility.dart';
import 'window_geometry.dart';
import 'window_shell.dart';

/// Трей + hide-to-tray. Не вызывать setProgressBar.
class DesktopShell with TrayListener, WindowListener {
  DesktopShell._();
  static final DesktopShell instance = DesktopShell._();

  Future<void> Function()? onBeforeExit;
  bool Function()? shouldHideToTray;

  var _trayInitialized = false;
  var _shuttingDown = false;

  bool get trayInitialized => _trayInitialized;
  String _labelShow = 'Показать';
  String _labelExit = 'Выход';
  String _tooltip = 'Argos Translate';
  final _windowSaver = WindowStateSaver();

  static bool get isSupported =>
      !kIsWeb && (Platform.isWindows || Platform.isLinux);

  Future<void> prepareWindowManager({
    required Size minSize,
    required String title,
  }) async {
    if (!isSupported) {
      return;
    }
    await windowManager.ensureInitialized();
    await windowManager.setPreventClose(true);
    await windowManager.waitUntilReadyToShow(
      WindowOptions(
        skipTaskbar: true,
        title: title,
        minimumSize: minSize,
        size: const Size(1000, 700),
      ),
      () async {
        // Видимость после первого кадра (applyLaunchVisibility).
      },
    );
  }

  void attachWindowListener() {
    if (!isSupported) {
      return;
    }
    windowManager.addListener(this);
  }

  Future<void> initTray({
    required String show,
    required String exit,
    String? tooltip,
  }) async {
    if (!isSupported || _trayInitialized) {
      return;
    }
    _labelShow = show;
    _labelExit = exit;
    if (tooltip != null) {
      _tooltip = tooltip;
    }
    try {
      await trayManager.setIcon(
        Platform.isWindows
            ? 'assets/icons/argos_translate.ico'
            : 'assets/icons/argos_translate.png',
      );
      await trayManager.setToolTip(_tooltip);
      await _rebuildMenu();
      trayManager.addListener(this);
      _trayInitialized = true;
    } catch (e, st) {
      AppLog.warning('Tray init failed', e, st);
    }
  }

  Future<void> _rebuildMenu() async {
    await trayManager.setContextMenu(
      Menu(
        items: [
          MenuItem(key: 'show', label: _labelShow),
          MenuItem.separator(),
          MenuItem(key: 'exit', label: _labelExit),
        ],
      ),
    );
  }

  Future<void> applyLaunchVisibility({required bool showWindow}) async {
    if (!isSupported) {
      return;
    }
    if (showWindow) {
      await WindowShell.showAndFocus();
    } else {
      await WindowShell.hideToTray();
    }
  }

  @override
  void onTrayIconMouseDown() {
    unawaited(WindowShell.showAndFocus());
  }

  @override
  void onTrayIconRightMouseDown() {
    trayManager.popUpContextMenu();
  }

  @override
  void onTrayMenuItemClick(MenuItem menuItem) {
    switch (menuItem.key) {
      case 'show':
        unawaited(WindowShell.showAndFocus());
      case 'exit':
        unawaited(shutdown());
    }
  }

  @override
  void onWindowClose() {
    _windowSaver.scheduleSave();
    final wantTray = shouldHideToTray?.call() ?? true;
    if (shouldHideWindowToTray(
      closeActionIsTray: wantTray,
      trayInitialized: _trayInitialized,
    )) {
      unawaited(WindowShell.hideToTray());
    } else if (wantTray) {
      AppLog.warning('Close-to-tray skipped — tray is not initialized');
      unawaited(WindowShell.showAndFocus());
    } else {
      unawaited(shutdown());
    }
  }

  @override
  void onWindowFocus() {
    unawaited(_ensureTaskbarVisible());
  }

  @override
  void onWindowRestore() {
    unawaited(_ensureTaskbarVisible());
  }

  @override
  void onWindowMoved() => _windowSaver.scheduleSave();

  @override
  void onWindowResized() => _windowSaver.scheduleSave();

  @override
  void onWindowMaximize() => _windowSaver.scheduleSave();

  @override
  void onWindowUnmaximize() => _windowSaver.scheduleSave();

  Future<void> _ensureTaskbarVisible() async {
    if (!isSupported || _shuttingDown) {
      return;
    }
    try {
      if (await windowManager.isVisible()) {
        await windowManager.setSkipTaskbar(false);
      }
    } catch (_) {
      // shutdown / race
    }
  }

  Future<void> shutdown() async {
    if (_shuttingDown) {
      return;
    }
    _shuttingDown = true;
    try {
      await onBeforeExit?.call();
    } catch (e, st) {
      AppLog.warning('onBeforeExit failed', e, st);
    }
    await destroyTray();
    try {
      await windowManager.setPreventClose(false);
      await windowManager.destroy();
    } catch (_) {
      // already gone
    }
    exit(0);
  }

  Future<void> destroyTray() async {
    if (!isSupported || !_trayInitialized) {
      return;
    }
    trayManager.removeListener(this);
    windowManager.removeListener(this);
    try {
      await trayManager.destroy();
    } catch (_) {}
    _trayInitialized = false;
  }
}
