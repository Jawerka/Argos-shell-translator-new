import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';
import 'package:translator_core/translator_core.dart';

void main() {
  test('parseSidecarHealthJson reads ok and version', () {
    final health = parseSidecarHealthJson('{"ok":true,"version":"1.0.0"}');
    expect(health.ok, isTrue);
    expect(health.version, '1.0.0');
  });

  test('parseSidecarHealthJson treats missing ok as false', () {
    final health = parseSidecarHealthJson('{"version":"x"}');
    expect(health.ok, isFalse);
    expect(health.version, 'x');
  });

  test('GET /health does not send token', () async {
    final client = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/health');
      expect(request.headers[sidecarTokenHeader], isNull);
      return http.Response('{"ok":true,"version":"1.0.0"}', 200);
    });
    final sidecar = SidecarClient(
      baseUri: Uri.parse('http://127.0.0.1:9'),
      token: 'secret-token',
      httpClient: client,
    );
    final health = await sidecar.getPublicHealth();
    expect(health.ok, isTrue);
    expect(health.version, '1.0.0');
  });

  test('GET /v1/health sends X-Sidecar-Token', () async {
    final client = MockClient((request) async {
      expect(request.url.path, '/v1/health');
      expect(request.headers[sidecarTokenHeader], 'secret-token');
      return http.Response(
        '{"ok":true,"version":"1.0.0","argos":false,"pairs":[]}',
        200,
      );
    });
    final sidecar = SidecarClient(
      baseUri: Uri.parse('http://127.0.0.1:9'),
      token: 'secret-token',
      httpClient: client,
    );
    final health = await sidecar.getAuthenticatedHealth();
    expect(health.ok, isTrue);
    expect(health.argos, isFalse);
  });
}
