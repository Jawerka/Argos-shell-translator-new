import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:translator/app.dart';
import 'package:translator/features/shell/main_split.dart';
import 'package:translator/providers.dart';
import 'package:translator_core/translator_core.dart';

http.Response jsonResponse(Object body, [int status = 200]) {
  return http.Response.bytes(
    utf8.encode(jsonEncode(body)),
    status,
    headers: {'content-type': 'application/json; charset=utf-8'},
  );
}

http.StreamedResponse jsonStreamed(Object body, [int status = 200]) {
  final bytes = utf8.encode(jsonEncode(body));
  return http.StreamedResponse(
    Stream<List<int>>.fromIterable([bytes]),
    status,
    headers: {'content-type': 'application/json; charset=utf-8'},
  );
}

/// Режим потока Argos для тестов.
enum FakeTranslateMode {
  /// start → chunk → done.
  success,

  /// start → chunk → error.
  error,

  /// start → error, без чанков (нет модели).
  missingPair,

  /// start → chunk → cancelled.
  cancelled,
}

class FakeSidecarOptions {
  FakeSidecarOptions({
    this.packagesDir = r'C:\Argos\packages',
    List<Object?> pairs = const ['en-ru'],
    this.decodeText = 'Hello',
    this.decodePath = r'C:\tmp\note.txt',
    this.detectCode = 'en',
    this.translateMode = FakeTranslateMode.success,
    this.translatedText = 'Привет',
    this.installSucceeds = true,
  }) : pairs = List<Object?>.from(pairs);

  final String packagesDir;
  List<Object?> pairs;
  final String decodeText;
  final String decodePath;
  final String detectCode;
  final FakeTranslateMode translateMode;
  final String translatedText;
  final bool installSucceeds;
}

class FakeSidecarState {
  FakeSidecarState(this.options);

  final FakeSidecarOptions options;
  var translateCalls = 0;
  var cancelCalls = 0;
  var installCalls = 0;
  var detectCalls = 0;
  var lastInstallBundle = false;
  final translateBodies = <Map<String, dynamic>>[];
}

SidecarClient fakeSidecar([FakeSidecarOptions? options]) {
  final opts = options ?? FakeSidecarOptions();
  final state = FakeSidecarState(opts);
  final client = SidecarClient(
    baseUri: Uri.parse('http://127.0.0.1:9'),
    token: 't',
    httpClient: MockClient.streaming((request, bodyStream) async {
      final path = request.url.path;
      final bodyBytes = await bodyStream.toBytes();
      final bodyText = bodyBytes.isEmpty ? '' : utf8.decode(bodyBytes);

      if (path == '/v1/translate') {
        state.translateCalls++;
        Map<String, dynamic> json = const {};
        if (bodyText.isNotEmpty) {
          json = jsonDecode(bodyText) as Map<String, dynamic>;
          state.translateBodies.add(json);
        }
        final from = json['from']?.toString() ?? 'auto';
        final to = json['to']?.toString() ?? 'ru';
        final detectedFrom = from == 'auto' ? opts.detectCode : from;

        Stream<List<int>> ndjsonStream() async* {
          yield utf8.encode(
            '{"type":"start","job_id":1,"from":"$detectedFrom","to":"$to","unit_count":1}\n',
          );
          switch (opts.translateMode) {
            case FakeTranslateMode.success:
              yield utf8.encode(
                '{"type":"chunk","job_id":1,"index":0,"para_idx":0,'
                '"text":${jsonEncode(opts.translatedText)},"done":1,"total":1}\n',
              );
              yield utf8.encode('{"type":"done","job_id":1}\n');
            case FakeTranslateMode.error:
              yield utf8.encode(
                '{"type":"chunk","job_id":1,"index":0,"para_idx":0,'
                '"text":${jsonEncode(opts.translatedText)},"done":1,"total":1}\n',
              );
              yield utf8.encode(
                '{"type":"error","job_id":1,"message":"argos failed"}\n',
              );
            case FakeTranslateMode.missingPair:
              yield utf8.encode(
                '{"type":"error","job_id":1,"message":"Нет модели nl→ru"}\n',
              );
            case FakeTranslateMode.cancelled:
              yield utf8.encode(
                '{"type":"chunk","job_id":1,"index":0,"para_idx":0,'
                '"text":${jsonEncode(opts.translatedText)},"done":1,"total":1}\n',
              );
              yield utf8.encode('{"type":"cancelled","job_id":1}\n');
          }
        }

        return http.StreamedResponse(
          ndjsonStream(),
          200,
          headers: {'content-type': 'application/x-ndjson'},
        );
      }

      if (path == '/v1/models') {
        return jsonStreamed({
          'pairs': opts.pairs,
          'packages_dir': opts.packagesDir,
        });
      }
      if (path == '/v1/health') {
        return jsonStreamed({
          'ok': true,
          'version': '1',
          'argos': opts.pairs.isNotEmpty,
          'pairs': opts.pairs,
          'packages_dir': opts.packagesDir,
        });
      }
      if (path == '/v1/languages') {
        return jsonStreamed({
          'languages': {'en': 'English', 'ru': 'Русский'},
        });
      }
      if (path == '/v1/files/decode') {
        return jsonStreamed({
          'text': opts.decodeText,
          'encoding': 'utf-8',
          'confidence': 1,
          'file_type': 'plain text',
          'path': opts.decodePath,
        });
      }
      if (path == '/v1/detect') {
        state.detectCalls++;
        return jsonStreamed({
          'code': opts.detectCode,
          'confidence': 0.99,
        });
      }
      if (path == '/v1/cancel') {
        state.cancelCalls++;
        return jsonStreamed({'ok': true});
      }
      if (path == '/v1/models/install') {
        state.installCalls++;
        if (bodyText.isNotEmpty) {
          final json = jsonDecode(bodyText) as Map<String, dynamic>;
          state.lastInstallBundle = json['bundle'] == true;
        }
        if (!opts.installSucceeds) {
          return jsonStreamed({'error': 'install failed'}, 500);
        }
        opts.pairs = <Object?>['en-ru'];
        return jsonStreamed({
          'ok': true,
          'installed': ['en-ru'],
          'pairs': opts.pairs,
        });
      }
      return jsonStreamed({'ok': true});
    }),
  );
  FakeSidecarClientX._states[client] = state;
  return client;
}

extension FakeSidecarClientX on SidecarClient {
  static final _states = Expando<FakeSidecarState>();

  FakeSidecarState get fakeState =>
      FakeSidecarClientX._states[this] ?? FakeSidecarState(FakeSidecarOptions());
}

enum FakeLlmMode { success, error, config }

class FakeLlmClient extends LlmClient {
  FakeLlmClient({
    this.models = const ['alpha', 'beta-llm'],
    this.mode = FakeLlmMode.success,
    this.tokens = const ['При', 'вет'],
    this.tokenDelay = Duration.zero,
  });

  final List<String> models;
  final FakeLlmMode mode;
  final List<String> tokens;
  final Duration tokenDelay;
  var translateCalls = 0;
  var fetchModelsCalls = 0;
  String? lastFromCode;
  String? lastToCode;
  String? lastText;

  @override
  Future<List<String>> fetchModels(
    LlmSettings settings, {
    Duration timeout = const Duration(seconds: 10),
  }) async {
    fetchModelsCalls++;
    if (!settings.enabled) {
      throw LlmDisabledException();
    }
    return List<String>.from(models);
  }

  @override
  Stream<String> translate({
    required LlmSettings settings,
    required String text,
    required String fromCode,
    required String toCode,
    required Map<String, String> languages,
    String? fileType,
    bool Function()? isCancelled,
    void Function(int done, int total)? onChunkProgress,
  }) async* {
    translateCalls++;
    lastFromCode = fromCode;
    lastToCode = toCode;
    lastText = text;
    if (!settings.enabled) {
      throw LlmDisabledException();
    }
    if (mode == FakeLlmMode.config) {
      throw LlmConfigException('адрес сервера не задан');
    }
    if (mode == FakeLlmMode.error) {
      throw LlmException('connection refused');
    }
    onChunkProgress?.call(0, 1);
    var acc = '';
    for (final token in tokens) {
      if (isCancelled?.call() ?? false) {
        throw LlmCancelledException();
      }
      if (tokenDelay > Duration.zero) {
        await Future<void>.delayed(tokenDelay);
      }
      acc += token;
      yield acc;
    }
    onChunkProgress?.call(1, 1);
  }
}

/// Настройки без LLM — чтобы Argos-сценарии не затирались llmNotConfigured.
const argosOnlySettings = AppSettings(
  llm: LlmSettings(enabled: false),
  firstRunDone: true,
);

Future<ProviderContainer> pumpApp(
  WidgetTester tester, {
  AppSettings? settings,
  LlmClient? llm,
  SidecarClient? sidecar,
}) async {
  tester.view.physicalSize = const Size(1400, 900);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final scope = ProviderScope(
    overrides: [
      if (settings != null)
        settingsProvider.overrideWith(() => SettingsController(settings)),
      if (llm != null) llmClientProvider.overrideWith((ref) => llm),
      if (sidecar != null) sidecarClientProvider.overrideWith((ref) => sidecar),
    ],
    child: const TranslatorApp(
      skipDesktopShell: true,
      skipSidecar: true,
    ),
  );
  await tester.pumpWidget(scope);
  await tester.pumpAndSettle();
  return ProviderScope.containerOf(tester.element(find.byType(MainSplit)));
}

Future<void> openSettings(WidgetTester tester) async {
  await tester.tap(find.byTooltip('Настройки'));
  await tester.pumpAndSettle();
}

Future<void> goSection(WidgetTester tester, String name) async {
  await tester.tap(find.byKey(Key('settings-nav-$name')));
  await tester.pumpAndSettle();
}
