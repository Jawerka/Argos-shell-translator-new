import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:path/path.dart' as p;
import 'package:test/test.dart';
import 'package:translator_core/translator_core.dart';

http.Response jsonUtf8Response(String body, int statusCode) {
  return http.Response.bytes(
    utf8.encode(body),
    statusCode,
    headers: {'content-type': 'application/json; charset=utf-8'},
  );
}

void main() {
  test('translate parses NDJSON events', () async {
    final client = MockClient.streaming((request, bodyStream) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/v1/translate');
      expect(request.headers[sidecarTokenHeader], 'secret-token');
      expect(request.headers['content-type'], contains('application/json'));
      final body = utf8.decode(await bodyStream.toBytes());
      final json = jsonDecode(body) as Map<String, dynamic>;
      expect(json['text'], 'Hello');
      expect(json['from'], 'en');
      expect(json['to'], 'ru');
      expect(json['prefer_api'], isTrue);
      expect(json['translate_code_blocks'], isFalse);
      expect(json['cache'], isFalse);
      expect(json['cache_size'], 500);

      const ndjson =
          '{"type":"start","job_id":1,"from":"en","to":"ru","unit_count":1}\n'
          '{"type":"chunk","job_id":1,"index":0,"para_idx":0,"text":"Привет","done":1,"total":1}\n'
          '{"type":"done","job_id":1}\n';
      return http.StreamedResponse(
        Stream<List<int>>.fromIterable([utf8.encode(ndjson)]),
        200,
        headers: {'content-type': 'application/x-ndjson'},
      );
    });
    final sidecar = SidecarClient(
      baseUri: Uri.parse('http://127.0.0.1:9'),
      token: 'secret-token',
      httpClient: client,
    );
    final events = await sidecar
        .translate(const TranslateRequest(text: 'Hello', fromCode: 'en'))
        .toList();
    expect(events, hasLength(3));
    final start = events[0] as TranslateStart;
    expect(start.jobId, 1);
    expect(start.fromCode, 'en');
    expect(start.toCode, 'ru');
    expect(start.unitCount, 1);
    final chunk = events[1] as TranslateChunk;
    expect(chunk.text, 'Привет');
    expect(chunk.done, 1);
    expect(chunk.total, 1);
    expect(events[2], isA<TranslateDone>());
  });

  test('TranslateRequest toJson includes cache_size', () {
    const request = TranslateRequest(
      text: 'Hello',
      fromCode: 'en',
      cache: true,
      cacheSize: 42,
    );
    expect(request.toJson()['cache'], isTrue);
    expect(request.toJson()['cache_size'], 42);
  });

  test('detect sends token', () async {
    final client = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/v1/detect');
      expect(request.headers[sidecarTokenHeader], 'secret-token');
      final json = jsonDecode(request.body) as Map<String, dynamic>;
      expect(json['text'], 'Привет');
      return jsonUtf8Response('{"code":"ru","label":"Русский"}', 200);
    });
    final sidecar = SidecarClient(
      baseUri: Uri.parse('http://127.0.0.1:9'),
      token: 'secret-token',
      httpClient: client,
    );
    final result = await sidecar.detect('Привет');
    expect(result.code, 'ru');
    expect(result.label, 'Русский');
  });

  test('unauthorized JSON becomes SidecarException', () async {
    final client = MockClient((request) async {
      return http.Response('{"error":"unauthorized"}', 401);
    });
    final sidecar = SidecarClient(
      baseUri: Uri.parse('http://127.0.0.1:9'),
      token: 'secret-token',
      httpClient: client,
    );
    expect(
      () => sidecar.detect('x'),
      throwsA(
        isA<SidecarException>().having(
          (e) => e.message,
          'message',
          'unauthorized',
        ),
      ),
    );
  });

  test('decodeFile posts path and max_size_mb', () async {
    final client = MockClient((request) async {
      expect(request.url.path, '/v1/files/decode');
      expect(request.headers[sidecarTokenHeader], 'secret-token');
      final json = jsonDecode(request.body) as Map<String, dynamic>;
      expect(json['path'], r'C:\tmp\note.txt');
      expect(json['max_size_mb'], 10);
      return http.Response(
        jsonEncode({
          'text': 'Hello',
          'encoding': 'utf-8',
          'confidence': 0.95,
          'file_type': 'plain text',
          'path': r'C:\tmp\note.txt',
        }),
        200,
      );
    });
    final sidecar = SidecarClient(
      baseUri: Uri.parse('http://127.0.0.1:9'),
      token: 'secret-token',
      httpClient: client,
    );
    final doc = await sidecar.decodeFile(path: r'C:\tmp\note.txt');
    expect(doc.text, 'Hello');
    expect(doc.encoding, 'utf-8');
    expect(doc.confidence, closeTo(0.95, 1e-9));
    expect(doc.fileType, 'plain text');
    expect(doc.path, r'C:\tmp\note.txt');
  });

  test('cancel body includes job_id', () async {
    final client = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/v1/cancel');
      expect(request.headers[sidecarTokenHeader], 'secret-token');
      final json = jsonDecode(request.body) as Map<String, dynamic>;
      expect(json['job_id'], 7);
      return http.Response('{"ok":true}', 200);
    });
    final sidecar = SidecarClient(
      baseUri: Uri.parse('http://127.0.0.1:9'),
      token: 'secret-token',
      httpClient: client,
    );
    await sidecar.cancel(jobId: 7);
  });

  test('languages returns map', () async {
    final client = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/v1/languages');
      expect(request.headers[sidecarTokenHeader], 'secret-token');
      return jsonUtf8Response(
        jsonEncode({
          'languages': {'en': 'English', 'ru': 'Русский'},
        }),
        200,
      );
    });
    final sidecar = SidecarClient(
      baseUri: Uri.parse('http://127.0.0.1:9'),
      token: 'secret-token',
      httpClient: client,
    );
    final langs = await sidecar.languages();
    expect(langs['en'], 'English');
    expect(langs['ru'], 'Русский');
  });

  test('error JSON on decodeFile', () async {
    final client = MockClient((request) async {
      return jsonUtf8Response('{"error":"нужен path"}', 400);
    });
    final sidecar = SidecarClient(
      baseUri: Uri.parse('http://127.0.0.1:9'),
      token: 't',
      httpClient: client,
    );
    expect(
      () => sidecar.decodeFile(path: ''),
      throwsA(
        isA<SidecarException>().having(
          (e) => e.message,
          'message',
          'нужен path',
        ),
      ),
    );
  });

  test('suggestOutputPath matches Python', () {
    expect(p.basename(suggestOutputPath('readme.md')), 'readme_translated.md');
    expect(
      p.basename(suggestOutputPath('readme.md', engine: 'llm')),
      'readme_translated_llm.md',
    );
  });

  test('supportedTextExtensions and defaultLanguageNames', () {
    expect(supportedTextExtensions, containsAll(['.txt', '.md', '.toml']));
    expect(isSupportedTextPath('notes.MD'), isTrue);
    expect(defaultLanguageNames['ru'], 'Русский');
    expect(defaultLanguageNames['en'], 'English');
  });

  test('translate parses error and cancelled NDJSON', () async {
    final client = MockClient.streaming((request, bodyStream) async {
      await bodyStream.drain<void>();
      const ndjson =
          '{"type":"error","job_id":3,"message":"Нет модели en→ru"}\n'
          '{"type":"cancelled","job_id":3}\n';
      return http.StreamedResponse(
        Stream<List<int>>.fromIterable([utf8.encode(ndjson)]),
        200,
        headers: {'content-type': 'application/x-ndjson'},
      );
    });
    final sidecar = SidecarClient(
      baseUri: Uri.parse('http://127.0.0.1:9'),
      token: 'secret-token',
      httpClient: client,
    );
    final events = await sidecar
        .translate(const TranslateRequest(text: 'Hello', fromCode: 'en'))
        .toList();
    expect(events[0], isA<TranslateError>());
    expect((events[0] as TranslateError).jobId, 3);
    expect((events[0] as TranslateError).message, contains('en→ru'));
    expect(events[1], isA<TranslateCancelled>());
  });

  test('translate idle timeout', () async {
    final controller = StreamController<List<int>>();
    addTearDown(() async {
      if (!controller.isClosed) {
        await controller.close();
      }
    });
    final client = MockClient.streaming((request, bodyStream) async {
      await bodyStream.drain<void>();
      return http.StreamedResponse(
        controller.stream,
        200,
        headers: {'content-type': 'application/x-ndjson'},
      );
    });
    final sidecar = SidecarClient(
      baseUri: Uri.parse('http://127.0.0.1:9'),
      token: 't',
      httpClient: client,
      translateIdleTimeout: const Duration(milliseconds: 40),
    );
    await expectLater(
      sidecar
          .translate(const TranslateRequest(text: 'Hello', fromCode: 'en'))
          .toList(),
      throwsA(
        isA<SidecarException>().having(
          (e) => e.message,
          'message',
          contains('таймаут'),
        ),
      ),
    );
  }, timeout: Timeout(const Duration(seconds: 5)));
}
