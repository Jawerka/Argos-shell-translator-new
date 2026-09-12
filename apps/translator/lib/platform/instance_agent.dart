import 'dart:async';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../core/app_log.dart';
import 'window_shell.dart';

/// Loopback-агент UI: фиксированный порт, если Win32 mutex fail-open.
const instanceAgentPort = 47821;

class InstanceAgent {
  InstanceAgent._();
  static final InstanceAgent instance = InstanceAgent._();

  HttpServer? _server;

  Future<void> start({required void Function() onShow}) async {
    _server = await HttpServer.bind(
      InternetAddress.loopbackIPv4,
      instanceAgentPort,
    );
    _server!.listen((request) async {
      try {
        if (request.method == 'GET' && request.uri.path == '/health') {
          request.response.statusCode = 200;
          request.response.write('{"ok":true}');
        } else if (request.method == 'POST' && request.uri.path == '/show') {
          onShow();
          request.response.statusCode = 200;
          request.response.write('{"ok":true}');
        } else {
          request.response.statusCode = 404;
        }
      } catch (e, st) {
        AppLog.warning('InstanceAgent request failed', e, st);
        request.response.statusCode = 500;
      } finally {
        await request.response.close();
      }
    });
    AppLog.info('InstanceAgent listening on 127.0.0.1:$instanceAgentPort');
  }

  Future<void> stop() async {
    await _server?.close(force: true);
    _server = null;
  }
}

class InstanceGate {
  InstanceGate({this.port = instanceAgentPort, http.Client? httpClient})
      : _http = httpClient ?? http.Client();

  final int port;
  final http.Client _http;

  Uri get _base => Uri.parse('http://127.0.0.1:$port');

  /// true — другой экземпляр принял фокус, этот процесс должен выйти.
  Future<bool> handoffIfRunning() async {
    if (!Platform.isWindows) {
      return false;
    }
    try {
      final health = await _http
          .get(_base.replace(path: '/health'))
          .timeout(const Duration(milliseconds: 400));
      if (health.statusCode != 200) {
        return false;
      }
      final res = await _http
          .post(_base.replace(path: '/show'))
          .timeout(const Duration(seconds: 2));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}

Future<void> startInstanceAgentOrHandoff() async {
  final gate = InstanceGate();
  if (await gate.handoffIfRunning()) {
    exit(0);
  }
  try {
    await InstanceAgent.instance.start(
      onShow: () {
        unawaited(WindowShell.showAndFocus());
      },
    );
  } catch (e, st) {
    AppLog.warning('InstanceAgent bind failed, retry handoff', e, st);
    if (await gate.handoffIfRunning()) {
      exit(0);
    }
  }
}
