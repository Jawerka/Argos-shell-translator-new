import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';
import 'package:translator_core/translator_core.dart';

void main() {
  test('split single short text', () {
    final chunks = splitLlmChunks('short text', 3000);
    expect(chunks.map((c) => c.translateText).toList(), ['short text']);
  });

  test('split multiple paragraphs', () {
    final para = 'word ' * 2000;
    final text = '$para\n\n$para';
    final chunks = splitLlmChunks(text, 3000);
    expect(chunks.length, greaterThanOrEqualTo(2));
  });

  test('disjoint coverage of three long paragraphs', () {
    final p1 = 'A' * 4000;
    final p2 = 'B' * 4000;
    final p3 = 'C' * 4000;
    final text = '$p1\n\n$p2\n\n$p3';
    final chunks = splitLlmChunks(text, 5000);
    expect(chunks.length, greaterThanOrEqualTo(2));
    final rebuilt = chunks.map((c) => c.translateText).join();
    expect(rebuilt, text);
  });

  test('long paragraph splits into sentence chunks', () {
    final text = 'Sentence one. ' * 1200;
    expect(text.length, greaterThan(15000));
    final chunks = splitLlmChunks(text, 3500);
    expect(chunks.length, greaterThanOrEqualTo(4));
    expect(chunks.every((c) => c.translateText.length <= 4000), isTrue);
  });

  test('context on second chunk', () {
    const p1 = 'First paragraph here.';
    const p2 = 'Second paragraph here.';
    final text = '$p1\n\n${'x' * 4000}\n\n$p2';
    final chunks = splitLlmChunks(text, 3500);
    expect(chunks.length, greaterThanOrEqualTo(2));
    expect(chunks[1].contextText, isNotEmpty);
  });

  test('joinChunkOutputs concatenates', () {
    expect(joinChunkOutputs(['TA', '\n\nTB']), 'TA\n\nTB');
  });

  test('adaptive limits', () {
    expect(adaptiveMaxTokens(1000, 4096), greaterThanOrEqualTo(4096));
    expect(
        adaptiveMaxTokens(3500, 4096, fileMode: true), lessThanOrEqualTo(2048));
    expect(
        adaptiveMaxTokens(5000, 4096, fileMode: true), lessThanOrEqualTo(2048));
    expect(
      adaptiveChunkTimeout(6000, 120, fileMode: true),
      greaterThanOrEqualTo(750),
    );
    expect(adaptiveChunkTimeout(6000, 120), greaterThanOrEqualTo(200));
  });

  test('parse SSE delta / reasoning / completions / DONE', () {
    expect(
      parseSseToken('data: {"choices":[{"delta":{"content":"Hi"}}]}'),
      'Hi',
    );
    expect(
      parseSseToken(
        'data: {"choices":[{"delta":{"reasoning_content":"Перевод"}}]}',
      ),
      'Перевод',
    );
    expect(
      parseSseToken('data: {"choices":[{"text":"Hi"}]}'),
      'Hi',
    );
    expect(parseSseToken('data: [DONE]'), isNull);
  });

  test('finalizeStreamText prefers content', () {
    expect(finalizeStreamText('Answer', 'Thinking'), 'Answer');
    expect(finalizeStreamText('', 'Fallback'), 'Fallback');
  });

  test('translatedTail', () {
    final text = 'word ' * 100;
    final tail = translatedTail(text, maxChars: 50);
    expect(tail.length, lessThanOrEqualTo(50));
    expect(text, contains(tail));
  });

  test('buildChunkUserContent with context', () {
    const chunk = LlmChunk(
      translateText: 'New part.',
      contextText: 'Old source.',
    );
    final content = buildChunkUserContent(
      chunk: chunk,
      chunkIndex: 1,
      total: 2,
      fileType: 'txt',
      translatedTailText: 'Previous translation.',
      useContext: true,
    );
    expect(content, contains('do not translate again'));
    expect(content, contains('Previous translation ended'));
    expect(content, contains('New part.'));
  });

  test('shouldFallbackToCompletions', () {
    expect(
      shouldFallbackToCompletions(404, 'chat/completions not found'),
      isTrue,
    );
    expect(shouldFallbackToCompletions(404, 'model not found'), isFalse);
  });

  test('buildSystemPrompt substitution and multi_part', () {
    const llm =
        LlmSettings(systemPrompt: 'From {source_code} to {target_code}');
    final result = buildSystemPrompt(
      llm,
      'en',
      'ru',
      {'en': 'English', 'ru': 'Russian'},
    );
    expect(result, contains('From en to ru'));

    const defaultLlm = LlmSettings();
    final multi = buildSystemPrompt(
      defaultLlm,
      'en',
      'ru',
      const {},
      multiPart: true,
    );
    expect(multi, contains('sequential parts'));
    expect(multi, contains('профессиональный переводчик'));
  });

  test('llmConfigError messages and no LAN fallback', () {
    const empty = LlmSettings();
    expect(resolveLlmBaseUrl(empty), isEmpty);
    expect(resolveLlmBaseUrl(empty).contains('192.168'), isFalse);
    expect(llmConfigError(empty), 'адрес сервера не задан');
    expect(llmConfigError(empty), isNot(contains('Base URL')));

    const openrouter = LlmSettings(
      provider: 'openrouter',
      baseUrl: 'https://openrouter.ai/api/v1',
    );
    expect(llmConfigError(openrouter), 'API-ключ обязателен для OpenRouter');

    const ok = LlmSettings(
      provider: 'local',
      baseUrl: 'http://127.0.0.1:8080/v1',
    );
    expect(llmConfigError(ok), isNull);
    expect(resolveLlmBaseUrl(ok), 'http://127.0.0.1:8080/v1');
  });

  test('SSE token assembly via MockClient.streaming', () async {
    final client = MockClient.streaming((request, bodyStream) async {
      await bodyStream.drain<void>();
      expect(request.url.path, endsWith('/chat/completions'));
      const sse = 'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
          'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
          'data: [DONE]\n\n';
      return http.StreamedResponse(
        Stream<List<int>>.fromIterable([utf8.encode(sse)]),
        200,
        headers: {'content-type': 'text/event-stream'},
      );
    });
    final llm = LlmClient(httpClient: client);
    final progress = <(int, int)>[];
    final events = await llm
        .translate(
          settings: const LlmSettings(
            enabled: true,
            provider: 'local',
            baseUrl: 'http://127.0.0.1:8080/v1',
            model: 'test',
          ),
          text: 'Hi',
          fromCode: 'en',
          toCode: 'ru',
          languages: const {'en': 'English', 'ru': 'Русский'},
          onChunkProgress: (done, total) => progress.add((done, total)),
        )
        .toList();
    expect(events.last, 'Hello');
    expect(progress.first, (0, 1));
    expect(progress.last, (1, 1));
  });

  test('chat 404 falls back to completions', () async {
    final urls = <String>[];
    final client = MockClient.streaming((request, bodyStream) async {
      await bodyStream.drain<void>();
      urls.add(request.url.path);
      if (request.url.path.endsWith('/chat/completions')) {
        return http.StreamedResponse(
          Stream<List<int>>.fromIterable(
            [utf8.encode('chat/completions not found')],
          ),
          404,
        );
      }
      expect(request.url.path.endsWith('/completions'), isTrue);
      final payload = jsonEncode({
        'choices': [
          {'text': 'Legacy'},
        ],
      });
      return http.StreamedResponse(
        Stream<List<int>>.fromIterable([utf8.encode(payload)]),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final llm = LlmClient(httpClient: client);
    final events = await llm.translate(
      settings: const LlmSettings(
        enabled: true,
        provider: 'local',
        baseUrl: 'http://127.0.0.1:8080/v1',
        model: 'test',
        stream: false,
      ),
      text: 'Hello',
      fromCode: 'en',
      toCode: 'ru',
      languages: const {},
    ).toList();
    expect(urls.any((u) => u.endsWith('/completions')), isTrue);
    expect(events.last, 'Legacy');
  });

  test('disabled LLM throws', () {
    final llm = LlmClient(
      httpClient: MockClient((request) async => http.Response('no', 500)),
    );
    expect(
      () => llm.translate(
        settings: const LlmSettings(enabled: false),
        text: 'Hi',
        fromCode: 'en',
        toCode: 'ru',
        languages: const {},
      ).toList(),
      throwsA(isA<LlmDisabledException>()),
    );
  });

  test('fetchModels reads data[].id', () async {
    final client = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/v1/models');
      return http.Response(
        jsonEncode({
          'data': [
            {'id': 'qwen3-8b'},
            {'id': 'llama-3.1-8b'},
          ],
        }),
        200,
      );
    });
    final llm = LlmClient(httpClient: client);
    final models = await llm.fetchModels(
      const LlmSettings(
        enabled: true,
        provider: 'local',
        baseUrl: 'http://127.0.0.1:8080/v1',
      ),
    );
    expect(models, ['qwen3-8b', 'llama-3.1-8b']);
  });
}
