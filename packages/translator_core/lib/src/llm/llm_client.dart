import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'package:http/http.dart' as http;

import '../json_util.dart';
import '../settings/app_settings.dart';
import '../utf8_lines.dart';
import 'llm_chunks.dart';
import 'llm_config.dart';
import 'llm_exceptions.dart';
import 'sse.dart';

export 'llm_exceptions.dart';

/// HTTP-клиент LLM (OpenAI-compatible chat + fallback /completions).
class LlmClient {
  LlmClient({http.Client? httpClient}) : _http = httpClient;

  final http.Client? _http;
  http.Client? _activeClient;

  /// Прервать in-flight HTTP (Stop / новый цикл).
  void abort() {
    final client = _activeClient;
    _activeClient = null;
    if (client == null) {
      return;
    }
    if (_http == null) {
      client.close();
    }
  }

  /// Нарастающий полный текст перевода (префикс + текущий чанк), как Python on_token.
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
    if (!settings.enabled) {
      throw LlmDisabledException();
    }
    final configErr = llmConfigError(settings);
    if (configErr != null) {
      throw LlmConfigException(configErr);
    }

    final client = _http ?? http.Client();
    final ownsClient = _http == null;
    _activeClient = client;
    try {
      final maxChars = chunkMaxChars(settings, fileType);
      final chunks = splitLlmChunks(text, maxChars);
      final useContext = fileType != null && settings.fileChunkContext;
      final systemPrompt = buildSystemPrompt(
        settings,
        fromCode,
        toCode,
        languages,
        multiPart: chunks.length > 1,
      );
      final baseUrl = resolveLlmBaseUrl(settings);
      final ctx = _LlmHttpContext(
        headers: llmAuthHeaders(settings),
        chatUrl: llmChatUrl(baseUrl),
        completionsUrl: llmCompletionsUrl(baseUrl),
        model: settings.model.trim().isEmpty ? 'default' : settings.model,
      );

      final fullParts = <String>[];
      var cancelled = false;
      onChunkProgress?.call(0, chunks.length);

      for (var chunkIdx = 0; chunkIdx < chunks.length; chunkIdx++) {
        if (isCancelled?.call() ?? false) {
          cancelled = true;
          break;
        }

        final chunk = chunks[chunkIdx];
        final tail = fullParts.isNotEmpty && useContext
            ? translatedTail(fullParts.last)
            : '';
        final userContent = buildChunkUserContent(
          chunk: chunk,
          chunkIndex: chunkIdx,
          total: chunks.length,
          fileType: fileType,
          translatedTailText: tail,
          useContext: useContext,
        );
        final prefix = joinChunkOutputs(fullParts);
        var chunkResult = '';
        try {
          await for (final acc in _requestChunkWithRetry(
            client: client,
            ctx: ctx,
            settings: settings,
            systemPrompt: systemPrompt,
            userContent: userContent,
            textLen: chunk.translateText.length,
            fileMode: fileType != null,
            isCancelled: isCancelled,
          )) {
            chunkResult = acc;
            yield prefix + acc;
          }
        } on Object catch (exc) {
          if (exc is LlmCancelledException || exc is LlmHttpException) {
            rethrow;
          }
          if (_isCancel(isCancelled) && chunkResult.trim().isNotEmpty) {
            fullParts.add(stripLeadingContextRepeat(chunkResult, tail));
            onChunkProgress?.call(fullParts.length, chunks.length);
            cancelled = true;
            break;
          }
          fullParts.add(_chunkErrorMarker(exc));
          onChunkProgress?.call(fullParts.length, chunks.length);
          yield joinChunkOutputs(fullParts);
          continue;
        }

        if (isCancelled?.call() ?? false) {
          if (chunkResult.trim().isNotEmpty) {
            fullParts.add(stripLeadingContextRepeat(chunkResult, tail));
            onChunkProgress?.call(fullParts.length, chunks.length);
          }
          cancelled = true;
          break;
        }

        chunkResult = stripLeadingContextRepeat(chunkResult, tail);
        if (chunkResult.trim().isEmpty) {
          if (isCancelled?.call() ?? false) {
            cancelled = true;
            break;
          }
          fullParts.add(llmEmptyChunkMarker);
          onChunkProgress?.call(fullParts.length, chunks.length);
          yield joinChunkOutputs(fullParts);
          continue;
        }
        fullParts.add(chunkResult);
        onChunkProgress?.call(fullParts.length, chunks.length);
      }

      if (fullParts.isEmpty) {
        if (cancelled) {
          throw LlmCancelledException();
        }
        throw LlmException('LLM: не удалось перевести');
      }
      yield joinChunkOutputs(fullParts);
    } finally {
      if (identical(_activeClient, client)) {
        _activeClient = null;
      }
      if (ownsClient) {
        client.close();
      }
    }
  }

  /// GET `/models` — список id для диалога выбора.
  Future<List<String>> fetchModels(
    LlmSettings settings, {
    Duration timeout = const Duration(seconds: 10),
  }) async {
    if (!settings.enabled) {
      throw LlmDisabledException();
    }
    final configErr = llmConfigError(settings);
    if (configErr != null) {
      throw LlmConfigException(configErr);
    }
    final client = _http ?? http.Client();
    final ownsClient = _http == null;
    try {
      final url = Uri.parse(llmModelsUrl(resolveLlmBaseUrl(settings)));
      final response = await client
          .get(url, headers: llmAuthHeaders(settings))
          .timeout(timeout);
      if (response.statusCode != 200) {
        throw LlmHttpException(response.statusCode, response.body);
      }
      final decoded = jsonDecode(response.body);
      if (decoded is! Map) {
        return const [];
      }
      final data = decoded['data'];
      if (data is! List) {
        return const [];
      }
      final models = <String>[];
      for (final item in data) {
        if (item is Map && item['id'] != null) {
          final id = item['id'].toString();
          if (id.isNotEmpty) {
            models.add(id);
          }
        }
      }
      return models;
    } finally {
      if (ownsClient) {
        client.close();
      }
    }
  }

  Stream<String> _requestChunkWithRetry({
    required http.Client client,
    required _LlmHttpContext ctx,
    required LlmSettings settings,
    required String systemPrompt,
    required String userContent,
    required int textLen,
    required bool fileMode,
    bool Function()? isCancelled,
  }) async* {
    final chunkTimeout = adaptiveChunkTimeout(
      textLen,
      settings.timeoutSec,
      fileMode: fileMode,
    );
    final maxTokens = adaptiveMaxTokens(
      textLen,
      settings.maxTokens,
      fileMode: fileMode,
    );
    final readTimeout = Duration(
      milliseconds: math.max(1, (chunkTimeout * 1000).round()),
    );
    Object? lastExc;

    for (var attempt = 0; attempt < 2; attempt++) {
      try {
        var last = '';
        await for (final acc in _requestChunk(
          client: client,
          ctx: ctx,
          settings: settings,
          systemPrompt: systemPrompt,
          userContent: userContent,
          maxTokens: maxTokens,
          readTimeout: readTimeout,
          isCancelled: isCancelled,
        )) {
          last = acc;
          yield acc;
        }
        if (last.trim().isEmpty &&
            settings.stream &&
            !(isCancelled?.call() ?? false)) {
          await for (final acc in _requestChunk(
            client: client,
            ctx: ctx,
            settings: settings,
            systemPrompt: systemPrompt,
            userContent: userContent,
            maxTokens: maxTokens,
            readTimeout: readTimeout,
            isCancelled: isCancelled,
            streamOverride: false,
          )) {
            last = acc;
            yield acc;
          }
        }
        return;
      } on TimeoutException catch (exc) {
        lastExc = exc;
        if (_isCancel(isCancelled)) {
          throw LlmCancelledException();
        }
        if (attempt == 0) {
          continue;
        }
        rethrow;
      } on SocketException catch (exc) {
        lastExc = exc;
        if (_isCancel(isCancelled)) {
          throw LlmCancelledException();
        }
        if (attempt == 0) {
          await Future<void>.delayed(const Duration(seconds: 1));
          continue;
        }
        rethrow;
      } on http.ClientException catch (exc) {
        lastExc = exc;
        if (_isCancel(isCancelled)) {
          throw LlmCancelledException();
        }
        if (attempt == 0) {
          await Future<void>.delayed(const Duration(seconds: 1));
          continue;
        }
        rethrow;
      } on LlmHttpException catch (exc) {
        if (_isCancel(isCancelled)) {
          throw LlmCancelledException();
        }
        if (exc.statusCode >= 500 || exc.statusCode == 429) {
          lastExc = exc;
          if (attempt == 0) {
            final wait = exc.statusCode == 429 ? 2 : 1;
            await Future<void>.delayed(Duration(seconds: wait));
            continue;
          }
        }
        rethrow;
      }
    }
    if (lastExc != null) {
      throw lastExc;
    }
    throw LlmException('unreachable');
  }

  Stream<String> _requestChunk({
    required http.Client client,
    required _LlmHttpContext ctx,
    required LlmSettings settings,
    required String systemPrompt,
    required String userContent,
    required int maxTokens,
    required Duration readTimeout,
    bool Function()? isCancelled,
    bool useCompletions = false,
    bool? streamOverride,
  }) async* {
    final useStream = streamOverride ?? settings.stream;
    final url = useCompletions ? ctx.completionsUrl : ctx.chatUrl;
    final Map<String, Object?> body;
    if (useCompletions) {
      body = {
        'model': ctx.model,
        'prompt': completionsPrompt(systemPrompt, userContent),
        'temperature': settings.temperature,
        'max_tokens': maxTokens,
        'stream': useStream,
      };
    } else {
      body = {
        'model': ctx.model,
        'messages': [
          {'role': 'system', 'content': systemPrompt},
          {'role': 'user', 'content': userContent},
        ],
        'temperature': settings.temperature,
        'max_tokens': maxTokens,
        'stream': useStream,
      };
      if (settings.provider == 'local') {
        body['chat_template_kwargs'] = {'enable_thinking': false};
      }
    }

    final request = http.Request('POST', Uri.parse(url))
      ..headers.addAll(ctx.headers)
      ..body = jsonEncode(body);

    final streamed =
        await client.send(request).timeout(const Duration(seconds: 10));

    if (streamed.statusCode == 429) {
      final errBody = await streamed.stream.bytesToString();
      throw LlmHttpException(429, errBody);
    }
    if (streamed.statusCode >= 400) {
      final errBody = await streamed.stream.bytesToString();
      if (!useCompletions &&
          shouldFallbackToCompletions(streamed.statusCode, errBody)) {
        yield* _requestChunk(
          client: client,
          ctx: ctx,
          settings: settings,
          systemPrompt: systemPrompt,
          userContent: userContent,
          maxTokens: maxTokens,
          readTimeout: readTimeout,
          isCancelled: isCancelled,
          useCompletions: true,
          streamOverride: streamOverride,
        );
        return;
      }
      throw LlmHttpException(streamed.statusCode, errBody);
    }

    if (useStream) {
      var contentAcc = '';
      var reasoningAcc = '';
      var chunkResult = '';
      await for (final line
          in utf8Lines(streamed.stream).timeout(readTimeout)) {
        if (isCancelled?.call() ?? false) {
          final finalized = finalizeStreamText(contentAcc, reasoningAcc);
          if (finalized.isNotEmpty) {
            yield finalized;
          }
          return;
        }
        if (line.isEmpty) {
          continue;
        }
        final sseError = parseSseErrorMessage(line);
        if (sseError != null) {
          throw LlmHttpException(500, sseError);
        }
        final (contentPiece, reasoningPiece) = parseSseParts(line);
        if (contentPiece.isNotEmpty) {
          contentAcc += contentPiece;
        }
        if (reasoningPiece.isNotEmpty) {
          reasoningAcc += reasoningPiece;
        }
        final display = contentAcc.isNotEmpty ? contentAcc : reasoningAcc;
        if (display != chunkResult) {
          chunkResult = display;
          yield chunkResult;
        }
      }
      chunkResult = finalizeStreamText(contentAcc, reasoningAcc);
      if (chunkResult.isNotEmpty) {
        yield chunkResult;
      }
    } else {
      final raw = await streamed.stream.bytesToString().timeout(readTimeout);
      final decoded = jsonDecode(raw);
      if (decoded is! Map) {
        return;
      }
      final chunkResult = extractNonStreamContent(asStringKeyedMap(decoded));
      if (chunkResult.isNotEmpty) {
        yield chunkResult;
      }
    }
  }
}

class _LlmHttpContext {
  const _LlmHttpContext({
    required this.headers,
    required this.chatUrl,
    required this.completionsUrl,
    required this.model,
  });

  final Map<String, String> headers;
  final String chatUrl;
  final String completionsUrl;
  final String model;
}

bool _isCancel(bool Function()? isCancelled) => isCancelled?.call() ?? false;

String _chunkErrorMessage(Object exc) {
  if (exc is TimeoutException) {
    return 'таймаут запроса';
  }
  if (exc is SocketException || exc is http.ClientException) {
    return 'нет соединения';
  }
  if (exc is LlmHttpException) {
    if (exc.statusCode == 429) {
      return 'занята (429)';
    }
    if (exc.statusCode == 404) {
      return 'модель не найдена';
    }
    return 'HTTP ${exc.statusCode}';
  }
  final text = '$exc';
  return text.length <= 80 ? text : text.substring(0, 80);
}

String _chunkErrorMarker(Object exc) =>
    '$llmChunkErrorPrefix${_chunkErrorMessage(exc)}]';
