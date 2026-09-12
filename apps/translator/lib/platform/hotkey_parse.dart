import 'package:flutter/services.dart';
import 'package:hotkey_manager/hotkey_manager.dart';

/// Разбор строки вида `ctrl+shift+c` → [HotKey].
///
/// Пустая строка / `ctrl+c` (обычный Copy) → null.
HotKey? parseGlobalHotkey(String raw) {
  final cleaned = raw.trim().toLowerCase().replaceAll(' ', '');
  if (cleaned.isEmpty) {
    return null;
  }
  final parts = cleaned.split('+').where((p) => p.isNotEmpty).toList();
  if (parts.isEmpty) {
    return null;
  }

  final keyToken = parts.last;
  final modifiers = <HotKeyModifier>[];
  for (final part in parts.take(parts.length - 1)) {
    switch (part) {
      case 'ctrl':
      case 'control':
        modifiers.add(HotKeyModifier.control);
      case 'shift':
        modifiers.add(HotKeyModifier.shift);
      case 'alt':
        modifiers.add(HotKeyModifier.alt);
      case 'meta':
      case 'win':
      case 'cmd':
      case 'super':
        modifiers.add(HotKeyModifier.meta);
      default:
        return null;
    }
  }

  final key = _logicalKey(keyToken);
  if (key == null) {
    return null;
  }

  // Не перехватывать обычный Copy (PRODUCT).
  if (key == LogicalKeyboardKey.keyC &&
      modifiers.length == 1 &&
      modifiers.first == HotKeyModifier.control) {
    return null;
  }

  return HotKey(
    key: key,
    modifiers: modifiers,
    scope: HotKeyScope.system,
  );
}

const _letterKeys = <LogicalKeyboardKey>[
  LogicalKeyboardKey.keyA,
  LogicalKeyboardKey.keyB,
  LogicalKeyboardKey.keyC,
  LogicalKeyboardKey.keyD,
  LogicalKeyboardKey.keyE,
  LogicalKeyboardKey.keyF,
  LogicalKeyboardKey.keyG,
  LogicalKeyboardKey.keyH,
  LogicalKeyboardKey.keyI,
  LogicalKeyboardKey.keyJ,
  LogicalKeyboardKey.keyK,
  LogicalKeyboardKey.keyL,
  LogicalKeyboardKey.keyM,
  LogicalKeyboardKey.keyN,
  LogicalKeyboardKey.keyO,
  LogicalKeyboardKey.keyP,
  LogicalKeyboardKey.keyQ,
  LogicalKeyboardKey.keyR,
  LogicalKeyboardKey.keyS,
  LogicalKeyboardKey.keyT,
  LogicalKeyboardKey.keyU,
  LogicalKeyboardKey.keyV,
  LogicalKeyboardKey.keyW,
  LogicalKeyboardKey.keyX,
  LogicalKeyboardKey.keyY,
  LogicalKeyboardKey.keyZ,
];

const _digitKeys = <LogicalKeyboardKey>[
  LogicalKeyboardKey.digit0,
  LogicalKeyboardKey.digit1,
  LogicalKeyboardKey.digit2,
  LogicalKeyboardKey.digit3,
  LogicalKeyboardKey.digit4,
  LogicalKeyboardKey.digit5,
  LogicalKeyboardKey.digit6,
  LogicalKeyboardKey.digit7,
  LogicalKeyboardKey.digit8,
  LogicalKeyboardKey.digit9,
];

LogicalKeyboardKey? _logicalKey(String token) {
  if (token.length == 1) {
    final ch = token.codeUnitAt(0);
    if (ch >= 0x61 && ch <= 0x7a) {
      return _letterKeys[ch - 0x61];
    }
    if (ch >= 0x30 && ch <= 0x39) {
      return _digitKeys[ch - 0x30];
    }
  }
  return switch (token) {
    'space' => LogicalKeyboardKey.space,
    'enter' || 'return' => LogicalKeyboardKey.enter,
    'tab' => LogicalKeyboardKey.tab,
    'escape' || 'esc' => LogicalKeyboardKey.escape,
    'f1' => LogicalKeyboardKey.f1,
    'f2' => LogicalKeyboardKey.f2,
    'f3' => LogicalKeyboardKey.f3,
    'f4' => LogicalKeyboardKey.f4,
    'f5' => LogicalKeyboardKey.f5,
    'f6' => LogicalKeyboardKey.f6,
    'f7' => LogicalKeyboardKey.f7,
    'f8' => LogicalKeyboardKey.f8,
    'f9' => LogicalKeyboardKey.f9,
    'f10' => LogicalKeyboardKey.f10,
    'f11' => LogicalKeyboardKey.f11,
    'f12' => LogicalKeyboardKey.f12,
    _ => null,
  };
}
