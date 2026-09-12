import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:hotkey_manager/hotkey_manager.dart';

import '../core/app_log.dart';
import 'hotkey_parse.dart';

/// Регистрация системного хоткея (Windows). Пустая строка — снять.
class GlobalHotkeyService {
  GlobalHotkeyService._();
  static final GlobalHotkeyService instance = GlobalHotkeyService._();

  HotKey? _registered;
  String _current = '';
  Future<void> Function()? onTriggered;

  static bool get isSupported =>
      !kIsWeb && Platform.isWindows && !Platform.environment.containsKey('FLUTTER_TEST');

  Future<void> sync(String raw) async {
    if (!isSupported) {
      return;
    }
    final next = raw.trim();
    if (next == _current && _registered != null) {
      return;
    }
    if (next == _current && next.isEmpty) {
      return;
    }

    await unregister();
    _current = next;
    if (next.isEmpty) {
      return;
    }

    final hotkey = parseGlobalHotkey(next);
    if (hotkey == null) {
      AppLog.warning('Invalid or blocked global hotkey: $next');
      return;
    }

    try {
      await hotKeyManager.register(
        hotkey,
        keyDownHandler: (_) {
          final cb = onTriggered;
          if (cb != null) {
            unawaited(cb());
          }
        },
      );
      _registered = hotkey;
      AppLog.info('Global hotkey registered: $next');
    } catch (e, st) {
      AppLog.warning('Failed to register hotkey $next', e, st);
      _registered = null;
    }
  }

  Future<void> unregister() async {
    final current = _registered;
    _registered = null;
    if (current == null || !isSupported) {
      return;
    }
    try {
      await hotKeyManager.unregister(current);
    } catch (e, st) {
      AppLog.warning('Failed to unregister hotkey', e, st);
    }
  }
}
