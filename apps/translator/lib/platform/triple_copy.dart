import 'dart:async';
import 'dart:io';
import 'dart:isolate';

import 'package:win32/win32.dart';

/// Детектор тройного Ctrl+C в окне [windowMs] (без SendInput).
class TripleCopyDetector {
  TripleCopyDetector({this.windowMs = 600});

  final int windowMs;
  final _presses = <({int atMs, int sequence})>[];

  bool registerPress({required int nowMs, required int sequence}) {
    _presses.add((atMs: nowMs, sequence: sequence));
    _presses.removeWhere((p) => nowMs - p.atMs > windowMs);
    if (_presses.length < 3) {
      return false;
    }
    final firstSeq = _presses.first.sequence;
    final changed = _presses.any((p) => p.sequence != firstSeq);
    _presses.clear();
    return changed;
  }

  void reset() => _presses.clear();
}

bool clipboardSequenceChanged({required int before, required int after}) {
  return after != before;
}

int readClipboardSequenceNumber() {
  if (!Platform.isWindows) {
    return 0;
  }
  try {
    return GetClipboardSequenceNumber();
  } catch (_) {
    return 0;
  }
}

class TripleCopyService {
  TripleCopyService._();

  static final TripleCopyService instance = TripleCopyService._();

  Isolate? _isolate;
  ReceivePort? _port;
  StreamSubscription<dynamic>? _sub;
  var _running = false;
  VoidCallback? onTriggered;

  Future<void> sync({required bool enabled}) async {
    if (!Platform.isWindows || !enabled) {
      await stop();
      return;
    }
    if (_running) {
      return;
    }
    await _start();
  }

  Future<void> _start() async {
    final port = ReceivePort();
    _port = port;
    _sub = port.listen((message) {
      if (message is int) {
        onTriggered?.call();
      }
    });
    _isolate = await Isolate.spawn(_tripleCopyIsolateMain, port.sendPort);
    _running = true;
  }

  Future<void> stop() async {
    _running = false;
    await _sub?.cancel();
    _sub = null;
    _port?.close();
    _port = null;
    _isolate?.kill(priority: Isolate.immediate);
    _isolate = null;
  }
}

typedef VoidCallback = void Function();

const _vkC = 0x43;

void _tripleCopyIsolateMain(SendPort sendPort) {
  final detector = TripleCopyDetector();
  var prevCDown = false;
  while (true) {
    final ctrlDown = (GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0;
    final cDown = (GetAsyncKeyState(_vkC) & 0x8000) != 0;
    if (ctrlDown && cDown && !prevCDown) {
      sleep(const Duration(milliseconds: 20));
      final now = DateTime.now().millisecondsSinceEpoch;
      final seq = GetClipboardSequenceNumber();
      if (detector.registerPress(nowMs: now, sequence: seq)) {
        sendPort.send(now);
      }
    }
    prevCDown = cDown;
    sleep(const Duration(milliseconds: 30));
  }
}
