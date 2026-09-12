import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../json_util.dart';
import '../utf8_lines.dart';
import 'sidecar_types.dart';

export 'sidecar_types.dart';

const sidecarTokenHeader = 'X-Sidecar-Token';

class SidecarException implements Exception {
  SidecarException(this.message);

  final String message;

  @override
  String toString() => message;
}

class SidecarHealth {
  const SidecarHealth({
    required this.ok,
    required this.version,
    this.argos,
    this.pairs = const [],
    this.packagesDir,
  });

  final bool ok;
  final String version;
  final bool? argos;
  final List<Object?> pairs;
  final String? packagesDir;

  factory SidecarHealth.fromJson(Map<String, dynamic> json) {
    final rawPairs = json['pairs'];
    return SidecarHealth(
      ok: json['ok'] == true,
      version: json['version']?.toString() ?? '',
      argos: json['argos'] is bool ? json['argos'] as bool : null,
      pairs: rawPairs is List ? List<Object?>.from(rawPairs) : const [],
      packagesDir: json['packages_dir'] is String
          ? json['packages_dir'] as String
          : null,
    );
  }
}

SidecarHealth parseSidecarHealthJson(String body) {
  final decoded = jsonDecode(body);
  if (decoded is! Map) {
    throw const FormatException('health JSON must be an object');
  }
  return SidecarHealth.fromJson(asStringKeyedMap(decoded));
}

class SidecarClient {
  SidecarClient({
    required this.baseUri,
    required this.token,
    http.Client? httpClient,
    this.jsonTimeout = const Duration(seconds: 10),
    this.installTimeout = const Duration(seconds: 120),
    this.translateIdleTimeout = const Duration(seconds: 180),
  }) : _injected = httpClient;

  final Uri baseUri;
  final String token;
  final Duration jsonTimeout;
  final Duration installTimeout;
  final Duration translateIdleTimeout;
  final http.Client? _injected;
  http.Client? _shared;
  final _inFlight = <http.Client>[];

  http.Client get _jsonClient => _injected ?? (_shared ??= http.Client());

  http.Client _streamClient() {
    final injected = _injected;
    if (injected != null) {
      return injected;
    }
    final client = http.Client();
    _inFlight.add(client);
    return client;
  }

  void _releaseStreamClient(http.Client client) {
    if (_injected != null) {
      return;
    }
    _inFlight.remove(client);
    client.close();
  }

  /// Прервать in-flight translate HTTP (Stop / новый цикл).
  void abortInFlight() {
    for (final client in List<http.Client>.from(_inFlight)) {
      client.close();
    }
    _inFlight.clear();
  }

  Future<SidecarHealth> getPublicHealth() async {
    final response = await _jsonClient
        .get(baseUri.resolve('/health'))
        .timeout(jsonTimeout);
    if (response.statusCode != 200) {
      throw SidecarException('GET /health → ${response.statusCode}');
    }
    return parseSidecarHealthJson(response.body);
  }

  Future<SidecarHealth> getAuthenticatedHealth() async {
    final response = await _jsonClient
        .get(
          baseUri.resolve('/v1/health'),
          headers: {sidecarTokenHeader: token},
        )
        .timeout(jsonTimeout);
    if (response.statusCode != 200) {
      throw SidecarException('GET /v1/health → ${response.statusCode}');
    }
    return parseSidecarHealthJson(response.body);
  }

  /// POST `/v1/translate` — поток NDJSON-событий.
  Stream<TranslateEvent> translate(TranslateRequest request) async* {
    final client = _streamClient();
    try {
      final req = http.Request('POST', baseUri.resolve('/v1/translate'))
        ..headers[sidecarTokenHeader] = token
        ..headers['Content-Type'] = 'application/json'
        ..body = jsonEncode(request.toJson());
      final response = await client.send(req).timeout(jsonTimeout);
      if (response.statusCode != 200) {
        final body = await response.stream.bytesToString();
        throw SidecarException(_sidecarErrorMessage(body, response.statusCode));
      }
      await for (final line in utf8Lines(
        response.stream.timeout(translateIdleTimeout),
      )) {
        final trimmed = line.trim();
        if (trimmed.isEmpty) {
          continue;
        }
        final decoded = jsonDecode(trimmed);
        if (decoded is! Map) {
          throw const FormatException('translate event JSON must be an object');
        }
        yield TranslateEvent.fromJson(asStringKeyedMap(decoded));
      }
    } on TimeoutException {
      throw SidecarException('таймаут sidecar');
    } finally {
      _releaseStreamClient(client);
    }
  }

  Future<DetectResult> detect(String text) async {
    final json = await _postJson('/v1/detect', {'text': text});
    return DetectResult.fromJson(json);
  }

  Future<Map<String, String>> languages() async {
    final json = await _getJson('/v1/languages');
    return SidecarLanguages.fromJson(json).languages;
  }

  Future<SidecarModels> listModels() async {
    final json = await _getJson('/v1/models');
    return SidecarModels.fromJson(json);
  }

  Future<DecodedDocument> decodeFile({
    required String path,
    int maxSizeMb = 10,
  }) async {
    final json = await _postJson('/v1/files/decode', {
      'path': path,
      'max_size_mb': maxSizeMb,
    });
    return DecodedDocument.fromJson(json);
  }

  Future<void> cancel({int? jobId}) async {
    final body = <String, Object?>{};
    if (jobId != null) {
      body['job_id'] = jobId;
    }
    await _postJson('/v1/cancel', body);
  }

  Future<InstallModelsResult> installModels({
    String? path,
    bool bundle = false,
  }) async {
    final body = <String, Object?>{'bundle': bundle};
    if (path != null) {
      body['path'] = path;
    }
    final json = await _postJson(
      '/v1/models/install',
      body,
      timeout: installTimeout,
    );
    return InstallModelsResult.fromJson(json);
  }

  void close() {
    abortInFlight();
    final injected = _injected;
    if (injected != null) {
      injected.close();
    } else {
      _shared?.close();
      _shared = null;
    }
  }

  Map<String, String> get _authHeaders => {sidecarTokenHeader: token};

  Future<Map<String, dynamic>> _getJson(String path) async {
    try {
      final response = await _jsonClient
          .get(
            baseUri.resolve(path),
            headers: _authHeaders,
          )
          .timeout(jsonTimeout);
      return _decodeChecked(response);
    } on TimeoutException {
      throw SidecarException('таймаут sidecar');
    }
  }

  Future<Map<String, dynamic>> _postJson(
    String path,
    Map<String, Object?> body, {
    Duration? timeout,
  }) async {
    try {
      final response = await _jsonClient
          .post(
            baseUri.resolve(path),
            headers: {
              ..._authHeaders,
              'Content-Type': 'application/json',
            },
            body: jsonEncode(body),
          )
          .timeout(timeout ?? jsonTimeout);
      return _decodeChecked(response);
    } on TimeoutException {
      throw SidecarException('таймаут sidecar');
    }
  }

  Map<String, dynamic> _decodeChecked(http.Response response) {
    if (response.statusCode != 200) {
      throw SidecarException(
        _sidecarErrorMessage(response.body, response.statusCode),
      );
    }
    final decoded = jsonDecode(response.body);
    if (decoded is! Map) {
      throw const FormatException('JSON must be an object');
    }
    return asStringKeyedMap(decoded);
  }
}

String _sidecarErrorMessage(String body, int statusCode) {
  try {
    final decoded = jsonDecode(body);
    if (decoded is Map && decoded['error'] != null) {
      return decoded['error'].toString();
    }
  } on FormatException {
    // тело не JSON — ниже общий HTTP-код
  }
  return 'HTTP $statusCode';
}
