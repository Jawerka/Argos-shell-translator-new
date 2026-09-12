import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:translator_core/translator_core.dart';

class AppLog {
  AppLog._();

  static IOSink? _sink;
  static const _maxBytes = 2 * 1024 * 1024;

  static Future<void> setup() async {
    try {
      final dir = ArgosPaths.logDir;
      await dir.create(recursive: true);
      final file = ArgosPaths.appLogFile;
      if (await file.exists()) {
        final length = await file.length();
        if (length > _maxBytes) {
          final backup = File('${file.path}.1');
          if (await backup.exists()) {
            await backup.delete();
          }
          await file.rename(backup.path);
        }
      }
      _sink = ArgosPaths.appLogFile.openWrite(mode: FileMode.append);
      FlutterError.onError = (details) {
        error('FlutterError', details.exception, details.stack);
        FlutterError.presentError(details);
      };
      PlatformDispatcher.instance.onError = (err, st) {
        error('uncaught', err, st);
        return true;
      };
      info('startup begin');
    } catch (e, st) {
      // ignore: avoid_print
      print('File logging failed: $e\n$st');
    }
  }

  static void info(String message) => _write('INFO', message);

  static void warning(String message, [Object? error, StackTrace? st]) {
    _write('WARN', message, error, st);
  }

  static void error(String message, [Object? err, StackTrace? st]) {
    _write('ERROR', message, err, st);
  }

  static void _write(
    String level,
    String message, [
    Object? error,
    StackTrace? st,
  ]) {
    final line = StringBuffer(
      '${DateTime.now().toIso8601String()} [$level] $message',
    );
    if (error != null) {
      line.write(' $error');
    }
    if (st != null) {
      line.write('\n$st');
    }
    final text = line.toString();
    _sink?.writeln(text);
    // ignore: avoid_print
    print(text);
  }

  static Future<void> close() async {
    await _sink?.flush();
    await _sink?.close();
    _sink = null;
  }
}
