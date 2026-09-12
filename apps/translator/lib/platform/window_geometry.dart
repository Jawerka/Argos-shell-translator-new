import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/painting.dart';
import 'package:path/path.dart' as p;
import 'package:translator_core/translator_core.dart';
import 'package:window_manager/window_manager.dart';

import '../core/app_log.dart';

class WindowStateStore {
  WindowStateStore._();

  static File get _file {
    final override = Platform.environment['ARGOS_CONFIG_DIR'];
    if (override != null && override.isNotEmpty) {
      return File(p.join(override, 'window_state.json'));
    }
    return ArgosPaths.windowStateFile;
  }

  static Future<WindowGeometry> load() async {
    try {
      final file = _file;
      if (!await file.exists()) {
        return WindowGeometry.defaults;
      }
      final map = jsonDecode(await file.readAsString());
      if (map is! Map) {
        return WindowGeometry.defaults;
      }
      return WindowGeometry.fromJson(
        map.map((key, value) => MapEntry(key.toString(), value)),
      );
    } catch (e, st) {
      AppLog.warning('WindowStateStore.load failed', e, st);
      return WindowGeometry.defaults;
    }
  }

  static Future<void> save(WindowGeometry geometry) async {
    final file = _file;
    await file.parent.create(recursive: true);
    await file.writeAsString(
      const JsonEncoder.withIndent('  ').convert(geometry.toJson()),
    );
  }

  static Rect toRect(WindowGeometry geometry) {
    return Rect.fromLTWH(
      geometry.left,
      geometry.top,
      geometry.width,
      geometry.height,
    );
  }
}

class WindowStateSaver {
  Timer? _debounce;

  void scheduleSave() {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () async {
      try {
        if (await windowManager.isMinimized()) {
          return;
        }
        final maximized = await windowManager.isMaximized();
        final bounds = await windowManager.getBounds();
        await WindowStateStore.save(
          WindowGeometry(
            left: bounds.left,
            top: bounds.top,
            width: bounds.width,
            height: bounds.height,
            maximized: maximized,
          ),
        );
      } catch (e, st) {
        AppLog.warning('WindowStateSaver failed', e, st);
      }
    });
  }

  void dispose() => _debounce?.cancel();
}
