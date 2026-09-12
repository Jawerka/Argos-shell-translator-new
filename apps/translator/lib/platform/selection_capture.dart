import 'dart:ffi';
import 'dart:io';

import 'package:ffi/ffi.dart';
import 'package:flutter/services.dart';
import 'package:win32/win32.dart';

import '../core/app_log.dart';

const _captureDelay = Duration(milliseconds: 80);

/// Симулировать Ctrl+C и прочитать буфер (как legacy CTk clipboard capture).
Future<String?> captureSelectionText({
  required bool restoreOriginal,
}) async {
  if (!Platform.isWindows) {
    return _readClipboard();
  }

  String? oldText;
  try {
    oldText = (await Clipboard.getData(Clipboard.kTextPlain))?.text;
  } catch (_) {}

  try {
    _sendCtrlC();
  } catch (e, st) {
    AppLog.warning('Ctrl+C simulation failed', e, st);
    return null;
  }

  await Future<void>.delayed(_captureDelay);

  final captured = await _readClipboard();
  if (restoreOriginal &&
      oldText != null &&
      captured != null &&
      captured != oldText) {
    try {
      await Clipboard.setData(ClipboardData(text: oldText));
    } catch (e, st) {
      AppLog.warning('clipboard restore failed', e, st);
    }
  }

  final text = captured?.trim();
  return (text == null || text.isEmpty) ? null : text;
}

Future<String?> _readClipboard() async {
  try {
    return (await Clipboard.getData(Clipboard.kTextPlain))?.text;
  } catch (e, st) {
    AppLog.warning('clipboard read failed', e, st);
    return null;
  }
}

void _sendCtrlC() {
  final inputs = calloc<INPUT>(4);
  try {
    void setKey(int index, int vk, {bool keyUp = false}) {
      inputs[index]
        ..type = INPUT_KEYBOARD
        ..ki.wVk = vk
        ..ki.wScan = 0
        ..ki.dwFlags = keyUp ? KEYEVENTF_KEYUP : 0
        ..ki.time = 0
        ..ki.dwExtraInfo = 0;
    }

    setKey(0, VK_CONTROL);
    setKey(1, VK_C);
    setKey(2, VK_C, keyUp: true);
    setKey(3, VK_CONTROL, keyUp: true);

    final sent = SendInput(4, inputs, sizeOf<INPUT>());
    if (sent != 4) {
      throw StateError('SendInput sent $sent of 4');
    }
  } finally {
    calloc.free(inputs);
  }
}
