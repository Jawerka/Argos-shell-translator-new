import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:translator_core/translator_core.dart';

import 'app_log.dart';

/// Единый диагностический лог детекции → detect.log (тот же файл, что у sidecar).
class DetectLog {
  DetectLog._();

  static IOSink? _sink;
  static String? _path;
  static const _maxBytes = 2 * 1024 * 1024;

  static String? get path => _path;

  /// Канонический путь: portable `{exe}/log/detect.log`, dev `{repo}/log/detect.log`,
  /// иначе `%USERPROFILE%\.argos_translate\log\detect.log`.
  static String resolvePath() {
    final fromEnv = Platform.environment['ARGOS_DETECT_LOG']?.trim();
    if (fromEnv != null && fromEnv.isNotEmpty) {
      return fromEnv;
    }

    final exeDir = File(Platform.resolvedExecutable).parent;
    final frozenCandidates = [
      p.join(exeDir.path, 'argos_sidecar.exe'),
      p.join(exeDir.path, 'sidecar', 'argos_sidecar.exe'),
    ];
    if (frozenCandidates.any((path) => File(path).existsSync())) {
      return p.join(exeDir.path, 'log', 'detect.log');
    }

    final repo = _findRepoRoot();
    if (repo != null) {
      return p.join(repo.path, 'log', 'detect.log');
    }

    return p.join(ArgosPaths.logDir.path, 'detect.log');
  }

  static Directory? _findRepoRoot() {
    var dir = Directory.current;
    for (var i = 0; i < 8; i++) {
      final marker = File(p.join(dir.path, 'sidecar', '__main__.py'));
      if (marker.existsSync()) {
        return dir;
      }
      final parent = dir.parent;
      if (parent.path == dir.path) {
        break;
      }
      dir = parent;
    }
    // Fallback: walk from executable (flutter test / run from build dir).
    dir = File(Platform.resolvedExecutable).parent;
    for (var i = 0; i < 10; i++) {
      final marker = File(p.join(dir.path, 'sidecar', '__main__.py'));
      if (marker.existsSync()) {
        return dir;
      }
      final parent = dir.parent;
      if (parent.path == dir.path) {
        break;
      }
      dir = parent;
    }
    return null;
  }

  static Future<void> setup({String? path}) async {
    try {
      final resolved = path ?? resolvePath();
      _path = resolved;
      final file = File(resolved);
      await file.parent.create(recursive: true);
      if (await file.exists()) {
        final length = await file.length();
        if (length > _maxBytes) {
          final backup = File('$resolved.1');
          if (await backup.exists()) {
            await backup.delete();
          }
          await file.rename(backup.path);
        }
      }
      await _sink?.flush();
      await _sink?.close();
      _sink = file.openWrite(mode: FileMode.append);
      info('path=$resolved');
      AppLog.info('DETECT path=$resolved');
    } catch (e, st) {
      AppLog.warning('DetectLog setup failed', e, st);
    }
  }

  static void info(String message) {
    final line =
        '${DateTime.now().toIso8601String()} - INFO - DETECT $message';
    try {
      _sink?.writeln(line);
    } catch (_) {}
  }

  static Future<void> close() async {
    await _sink?.flush();
    await _sink?.close();
    _sink = null;
  }
}
