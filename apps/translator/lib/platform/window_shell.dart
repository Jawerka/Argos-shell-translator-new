import 'package:flutter/material.dart';
import 'package:window_manager/window_manager.dart';

import '../core/app_log.dart';

/// Show/hide без setProgressBar (ACCESS_VIOLATION на части Windows).
class WindowShell {
  WindowShell._();

  static Future<void> showAndFocus() async {
    try {
      await windowManager.setSkipTaskbar(false);
      await windowManager.show();
      await windowManager.focus();
    } catch (e, st) {
      AppLog.warning('Window show/focus failed', e, st);
    }
  }

  static Future<void> hideToTray() async {
    try {
      await windowManager.setSkipTaskbar(true);
      await windowManager.hide();
    } catch (e, st) {
      AppLog.warning('Window hide failed', e, st);
    }
  }

  static Future<void> setOpacity(double opacity) async {
    try {
      await windowManager.setOpacity(opacity.clamp(0.3, 1.0));
    } catch (e, st) {
      AppLog.warning('Window opacity failed', e, st);
    }
  }

  static Future<void> applyBounds(Rect bounds, {required bool maximized}) async {
    try {
      await windowManager.setBounds(bounds);
      if (maximized) {
        await windowManager.maximize();
      }
    } catch (e, st) {
      AppLog.warning('Window setBounds failed', e, st);
    }
  }
}
