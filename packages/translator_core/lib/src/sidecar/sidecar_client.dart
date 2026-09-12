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
  }) : _http = httpClient ?? http.Client();

  final Uri baseUri;
  final String token;
  final http.Client _http;

  Future<SidecarHealth> getPublicHealth() async {
    final response = await _http.get(baseUri.resolve('/health'));
    if (response.statusCode != 200) {
      throw SidecarException('GET /health → ${response.statusCode}');
    }
    return parseSidecarHealthJson(response.body);
  }

  Future<SidecarHealth> getAuthenticatedHealth() async {
    final response = await _http.get(
      baseUri.resolve('/v1/health'),
      headers: {sidecarTokenHeader: token},
    );
    if (response.statusCode != 200) {
      throw SidecarException('GET /v1/health → ${response.statusCode}');
    }
    return parseSidecarHealthJson(response.body);
  }

  /// POST `/v1/translate` — поток NDJSON-событий.
  Stream<TranslateEvent> translate(TranslateRequest request) async* {
    final req = http.Request('POST', baseUri.resolve('/v1/translate'))
      ..headers[sidecarTokenHeader] = token
      ..headers['Content-Type'] = 'application/json'
      ..body = jsonEncode(request.toJson());
    final response = await _http.send(req);
    if (response.statusCode != 200) {
      final body = await response.stream.bytesToString();
      throw SidecarException(_sidecarErrorMessage(body, response.statusCode));
    }
    await for (final line in utf8Lines(response.stream)) {
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
    final json = await _postJson('/v1/models/install', body);
    return InstallModelsResult.fromJson(json);
  }

  void close() => _http.close();

  Map<String, String> get _authHeaders => {sidecarTokenHeader: token};

  Future<Map<String, dynamic>> _getJson(String path) async {
    final response = await _http.get(
      baseUri.resolve(path),
      headers: _authHeaders,
    );
    return _decodeChecked(response);
  }

  Future<Map<String, dynamic>> _postJson(
    String path,
    Map<String, Object?> body,
  ) async {
    final response = await _http.post(
      baseUri.resolve(path),
      headers: {
        ..._authHeaders,
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
    return _decodeChecked(response);
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
