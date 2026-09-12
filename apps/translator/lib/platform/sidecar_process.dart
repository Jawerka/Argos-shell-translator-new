import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:path/path.dart' as p;
import 'package:translator_core/translator_core.dart';

import '../core/app_log.dart';

class SidecarSession {
  SidecarSession({
    required this.port,
    required this.token,
    this.process,
  });

  final int port;
  final String token;
  final Process? process;

  Uri get baseUri => Uri.parse('http://127.0.0.1:$port');
}

class SidecarSpawnException implements Exception {
  SidecarSpawnException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Кандидаты frozen EXE рядом с Flutter: корень и подпапка sidecar/.
List<String> sidecarLaunchCandidates(Directory exeDir) {
  return [
    p.join(exeDir.path, 'argos_sidecar.exe'),
    p.join(exeDir.path, 'sidecar', 'argos_sidecar.exe'),
  ];
}

File? resolveFrozenSidecar(Directory exeDir) {
  for (final path in sidecarLaunchCandidates(exeDir)) {
    final file = File(path);
    if (file.existsSync()) {
      return file;
    }
  }
  return null;
}

File sidecarReadyFile(int pid, {String? tempDir}) {
  final dir = tempDir ?? Directory.systemTemp.path;
  return File(p.join(dir, 'argos-sidecar-ready-$pid.json'));
}

Map<String, dynamic>? parseSidecarReadyJson(String source) {
  final trimmed = source.trim();
  if (trimmed.isEmpty) {
    return null;
  }
  try {
    final decoded = jsonDecode(trimmed);
    if (decoded is! Map) {
      return null;
    }
    final ready = decoded.map((key, value) => MapEntry(key.toString(), value));
    if (ready['ok'] != true || ready['port'] is! num) {
      return null;
    }
    return ready;
  } catch (_) {
    return null;
  }
}

class SidecarRestartBudget {
  SidecarRestartBudget({
    this.maxAttempts = 3,
    this.window = const Duration(minutes: 1),
  });

  final int maxAttempts;
  final Duration window;
  final _times = <DateTime>[];

  /// null — лимит исчерпан; иначе пауза перед следующим spawn.
  Duration? nextDelay(DateTime now) {
    _times.removeWhere((t) => now.difference(t) >= window);
    if (_times.length >= maxAttempts) {
      return null;
    }
    final attempt = _times.length;
    _times.add(now);
    return Duration(milliseconds: 250 * (1 << attempt));
  }

  void reset() => _times.clear();
}

class SidecarProcess {
  SidecarProcess({this.disabled = false});

  factory SidecarProcess.disabled() => SidecarProcess(disabled: true);

  static const skipFromEnvironment = bool.fromEnvironment(
    'ARGOS_SKIP_SIDECAR',
    defaultValue: false,
  );

  final bool disabled;
  SidecarSession? _session;
  var _stopping = false;
  final _restart = SidecarRestartBudget();
  void Function(SidecarSession? session)? onSessionChanged;
  void Function()? onRestarting;
  void Function(Object error)? onRestartFailed;

  SidecarSession? get session => _session;

  Future<SidecarSession?> start({String? packagesDir}) async {
    if (disabled || skipFromEnvironment) {
      AppLog.info('Sidecar skipped');
      return null;
    }
    _stopping = false;
    _restart.reset();
    return _spawn(packagesDir: packagesDir, watchExit: true);
  }

  Future<SidecarSession?> _spawn({
    required String? packagesDir,
    required bool watchExit,
  }) async {
    final token = _randomToken();
    final resolved = _resolveLaunch(
      packagesDir: packagesDir,
      parentPid: pid,
    );
    AppLog.info('Starting sidecar: ${resolved.executable} ${resolved.arguments.join(' ')}');

    final environment = Map<String, String>.from(Platform.environment)
      ..['PYTHONUNBUFFERED'] = '1'
      ..['PYTHONIOENCODING'] = 'utf-8'
      ..['ARGOS_SIDECAR_TOKEN'] = token;
    final pythonPath = _pythonPath(resolved.workingDirectory);
    if (pythonPath != null) {
      environment['PYTHONPATH'] = pythonPath;
    }

    final process = await Process.start(
      resolved.executable,
      resolved.arguments,
      workingDirectory: resolved.workingDirectory,
      environment: environment,
      includeParentEnvironment: true,
    );

    var stderrLines = 0;
    process.stderr.transform(utf8.decoder).transform(const LineSplitter()).listen((line) {
      if (line.trim().isEmpty || stderrLines >= 200) {
        return;
      }
      stderrLines++;
      AppLog.warning('sidecar stderr: $line');
    });

    late final Map<String, dynamic> ready;
    try {
      ready = await _awaitReady(process);
    } on SidecarSpawnException {
      process.kill();
      rethrow;
    }

    final port = (ready['port'] as num).toInt();
    _deleteReadyFile(process.pid);
    final session = SidecarSession(port: port, token: token, process: process);
    _session = session;

    final client = SidecarClient(baseUri: session.baseUri, token: token);
    try {
      final publicHealth = await client.getPublicHealth();
      if (!publicHealth.ok) {
        throw SidecarSpawnException('GET /health вернул ok=false');
      }
      final authHealth = await client.getAuthenticatedHealth();
      if (!authHealth.ok) {
        throw SidecarSpawnException('GET /v1/health вернул ok=false');
      }
      AppLog.info('Sidecar ready on port $port version=${authHealth.version}');
    } catch (e) {
      await stop();
      throw SidecarSpawnException('Проверка sidecar не удалась: $e');
    } finally {
      client.close();
    }
    if (watchExit) {
      _watchExit(process, packagesDir: packagesDir);
    }
    onSessionChanged?.call(session);
    return session;
  }

  void _watchExit(Process process, {String? packagesDir}) {
    unawaited(process.exitCode.then((code) async {
      _deleteReadyFile(process.pid);
      if (_stopping) {
        return;
      }
      AppLog.warning('sidecar exited unexpectedly with code $code');
      onRestarting?.call();
      final delay = _restart.nextDelay(DateTime.now());
      if (delay == null) {
        onRestartFailed?.call(
          SidecarSpawnException('sidecar падал слишком часто'),
        );
        return;
      }
      await Future<void>.delayed(delay);
      if (_stopping) {
        return;
      }
      try {
        await _spawn(packagesDir: packagesDir, watchExit: true);
      } catch (e, st) {
        AppLog.error('sidecar restart failed', e, st);
        onRestartFailed?.call(e);
      }
    }));
  }

  Future<void> stop() async {
    _stopping = true;
    final process = _session?.process;
    _session = null;
    if (process == null) {
      return;
    }
    _deleteReadyFile(process.pid);
    try {
      process.kill();
      await process.exitCode.timeout(const Duration(seconds: 3));
    } catch (_) {
      try {
        process.kill(ProcessSignal.sigkill);
      } catch (_) {}
    }
  }

  _LaunchSpec _resolveLaunch({
    String? packagesDir,
    int? parentPid,
  }) {
    final envBin = Platform.environment['ARGOS_SIDECAR_BIN'];
    if (envBin != null && envBin.isNotEmpty) {
      return _LaunchSpec(
        executable: envBin,
        arguments: buildSidecarLaunchArgs(
          packagesDir: packagesDir,
          parentPid: parentPid,
        ),
        workingDirectory: File(envBin).parent.path,
      );
    }

    final exeDir = File(Platform.resolvedExecutable).parent;
    final frozen = resolveFrozenSidecar(exeDir);
    if (frozen != null) {
      return _LaunchSpec(
        executable: frozen.path,
        arguments: buildSidecarLaunchArgs(
          packagesDir: packagesDir,
          parentPid: parentPid,
        ),
        workingDirectory: frozen.parent.path,
      );
    }

    final repoRoot = findRepoRoot();
    if (repoRoot == null) {
      throw SidecarSpawnException(
        'Не найден корень репозитория (sidecar/__main__.py).',
      );
    }
    final python = resolvePython(repoRoot);
    if (python == null) {
      throw SidecarSpawnException(
        'Не найден Python 3.10 / venv (не используем 3.14).',
      );
    }
    return _LaunchSpec(
      executable: python,
      arguments: [
        '-u',
        '-m',
        'sidecar',
        ...buildSidecarLaunchArgs(
          packagesDir: packagesDir,
          parentPid: parentPid,
        ),
      ],
      workingDirectory: repoRoot.path,
    );
  }
}

/// Аргументы CLI sidecar (для spawn и тестов). Токен — через ARGOS_SIDECAR_TOKEN.
List<String> buildSidecarLaunchArgs({
  String? token,
  String? packagesDir,
  int? parentPid,
}) {
  final args = <String>[
    '--host',
    '127.0.0.1',
    '--port',
    '0',
  ];
  if (token != null && token.isNotEmpty) {
    args.addAll(['--token', token]);
  }
  final dir = packagesDir?.trim() ?? '';
  if (dir.isNotEmpty) {
    args.addAll(['--packages-dir', dir]);
  }
  if (parentPid != null && parentPid > 0) {
    args.addAll(['--parent-pid', '$parentPid']);
  }
  return args;
}

Future<Map<String, dynamic>> _awaitReady(
  Process process,
) async {
  final stderrBuf = StringBuffer();
  final ready = Completer<Map<String, dynamic>>();

  void completeFromFile() {
    if (ready.isCompleted) {
      return;
    }
    final file = sidecarReadyFile(process.pid);
    if (!file.existsSync()) {
      return;
    }
    try {
      final parsed = parseSidecarReadyJson(file.readAsStringSync());
      if (parsed != null && !ready.isCompleted) {
        ready.complete(parsed);
      }
    } on FileSystemException {
      return;
    }
  }

  void fail(String message) {
    if (!ready.isCompleted) {
      ready.completeError(SidecarSpawnException(message));
    }
  }

  process.stdout
      .transform(utf8.decoder)
      .transform(const LineSplitter())
      .listen(
    (line) {
      if (ready.isCompleted) {
        return;
      }
      final parsed = parseSidecarReadyJson(line);
      if (parsed != null) {
        ready.complete(parsed);
        return;
      }
      completeFromFile();
    },
    onDone: () {
      // Frozen console=False может закрыть stdout до JSON; ждём файл или timeout.
      completeFromFile();
    },
    onError: (Object e, StackTrace st) {
      completeFromFile();
      if (!ready.isCompleted) {
        ready.completeError(e, st);
      }
    },
  );

  unawaited(process.exitCode.then((code) {
    completeFromFile();
    fail('sidecar завершился с кодом $code. ${stderrBuf.toString().trim()}');
  }));

  final poll = Timer.periodic(const Duration(milliseconds: 200), (_) {
    completeFromFile();
  });

  try {
    return await ready.future.timeout(const Duration(seconds: 90));
  } on TimeoutException {
    completeFromFile();
    if (ready.isCompleted) {
      return await ready.future;
    }
    process.kill();
    throw SidecarSpawnException(
      'sidecar не ответил за 90 с. ${stderrBuf.toString().trim()}',
    );
  } finally {
    poll.cancel();
  }
}

void _deleteReadyFile(int processPid) {
  try {
    final file = sidecarReadyFile(processPid);
    if (file.existsSync()) {
      file.deleteSync();
    }
  } catch (_) {}
}

String? _pythonPath(String workingDirectory) {
  final root = Directory(workingDirectory);
  final sidecarMain = File(p.join(root.path, 'sidecar', '__main__.py'));
  final repo = sidecarMain.existsSync() ? root : findRepoRoot(start: root);
  if (repo == null) {
    return null;
  }
  final parts = <String>[
    repo.path,
    p.join(repo.path, 'src'),
  ];
  final existing = Platform.environment['PYTHONPATH'];
  if (existing != null && existing.isNotEmpty) {
    parts.add(existing);
  }
  return parts.join(Platform.isWindows ? ';' : ':');
}

class _LaunchSpec {
  const _LaunchSpec({
    required this.executable,
    required this.arguments,
    required this.workingDirectory,
  });

  final String executable;
  final List<String> arguments;
  final String workingDirectory;
}

String _randomToken() {
  final random = Random.secure();
  final bytes = List<int>.generate(16, (_) => random.nextInt(256));
  return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
}

Directory? findRepoRoot({Directory? start}) {
  final seeds = <Directory>[
    if (start != null) start,
    Directory.current,
    File(Platform.resolvedExecutable).parent,
  ];
  for (final seed in seeds) {
    var dir = seed;
    for (var i = 0; i < 14; i++) {
      final sidecarMain = File(p.join(dir.path, 'sidecar', '__main__.py'));
      final pubspec = File(p.join(dir.path, 'pubspec.yaml'));
      if (sidecarMain.existsSync()) {
        return dir;
      }
      if (pubspec.existsSync()) {
        final text = pubspec.readAsStringSync();
        if (text.contains('argos_translator_workspace')) {
          return dir;
        }
      }
      final parent = dir.parent;
      if (parent.path == dir.path) {
        break;
      }
      dir = parent;
    }
  }
  return null;
}

String? resolvePython(Directory repoRoot) {
  final venv = File(p.join(repoRoot.path, 'venv', 'Scripts', 'python.exe'));
  if (venv.existsSync()) {
    return venv.path;
  }
  const py310 = r'C:\Program Files\Python310\python.exe';
  if (File(py310).existsSync()) {
    return py310;
  }
  for (final name in ['Python312', 'Python311', 'Python310']) {
    final candidate = File(p.join(r'C:\Program Files', name, 'python.exe'));
    if (candidate.existsSync()) {
      return candidate.path;
    }
  }
  return null;
}
