import '../settings/app_settings.dart';

/// Шаблон системного промпта (точный текст Python DEFAULT_SYSTEM_PROMPT).
const defaultSystemPrompt = '''Ты — профессиональный переводчик.

Задача: переведи текст пользователя с языка «{source_lang}» ({source_code}) на язык «{target_lang}» ({target_code}).

Правила:
1. Выводи ТОЛЬКО перевод — без пояснений, примечаний и метаданных.
2. Сохраняй структуру оригинала: абзацы, переносы строк, списки, нумерацию.
3. Для Markdown (заголовки #, код ```, ссылки) сохраняй разметку; переводи только видимый текст.
4. Имена собственные, бренды, URL — оставляй как в оригинале, если нет устоявшегося перевода.
5. Сохраняй тон и стиль оригинала (нейтральный / формальный / разговорный).
6. Не добавляй контент, которого нет в исходном тексте.
7. Если текст уже на целевом языке — верни его без изменений.

Языки заданы настройками приложения. Следуй им строго.''';

const llmChunkErrorPrefix = '[LLM Error: ';
const llmEmptyChunkMarker = '[LLM Error: пустой ответ]';
const llmContextTailChars = 300;
const llmStripPrefixMin = 80;

String currentApiKey(LlmSettings llm) =>
    (llm.apiKeys[llm.provider] ?? '').trim();

/// Убрать завершающие `/`. Не трогает LAN-IP по умолчанию.
String stripTrailingSlashes(String url) {
  var result = url.trim();
  while (result.endsWith('/')) {
    result = result.substring(0, result.length - 1);
  }
  return result;
}

/// baseUrl, иначе providerUrls[provider]. Пусто — ошибка конфига (без LAN fallback).
String resolveLlmBaseUrl(LlmSettings llm) {
  final explicit = llm.baseUrl.trim();
  if (explicit.isNotEmpty) {
    return stripTrailingSlashes(explicit);
  }
  return stripTrailingSlashes(llm.providerUrls[llm.provider] ?? '');
}

/// Проверка конфига до HTTP. `enabled` здесь не проверяется.
String? llmConfigError(LlmSettings llm) {
  if (resolveLlmBaseUrl(llm).isEmpty) {
    return 'адрес сервера не задан';
  }
  if (llm.provider == 'openrouter' && currentApiKey(llm).isEmpty) {
    return 'API-ключ обязателен для OpenRouter';
  }
  return null;
}

String buildSystemPrompt(
  LlmSettings llm,
  String fromCode,
  String toCode,
  Map<String, String> languages, {
  bool multiPart = false,
}) {
  var template = llm.systemPrompt.trim();
  if (template.isEmpty) {
    template = defaultSystemPrompt;
  }
  final sourceLang = languages[fromCode] ?? fromCode.toUpperCase();
  final targetLang = languages[toCode] ?? toCode.toUpperCase();
  var prompt = template
      .replaceAll('{source_lang}', sourceLang)
      .replaceAll('{target_lang}', targetLang)
      .replaceAll('{source_code}', fromCode)
      .replaceAll('{target_code}', toCode)
      .replaceAll('{formality}', 'neutral');
  if (multiPart) {
    prompt +=
        '\n\nThe document is split into sequential parts; translate each part once. '
        'Keep terminology consistent with any provided context.';
  }
  return prompt;
}

Map<String, String> llmAuthHeaders(LlmSettings llm) {
  final headers = <String, String>{'Content-Type': 'application/json'};
  final key = currentApiKey(llm);
  final authMode = llm.authHeader;

  final bool sendAuth;
  if (authMode == 'auto') {
    sendAuth = key.isNotEmpty && llm.provider != 'local';
  } else {
    sendAuth = key.isNotEmpty;
  }

  if (sendAuth && key.isNotEmpty) {
    if (authMode == 'api-key') {
      headers['api-key'] = key;
    } else {
      headers['Authorization'] = 'Bearer $key';
    }
  }

  if (llm.provider == 'openrouter') {
    headers.putIfAbsent(
      'HTTP-Referer',
      () => 'https://argos-translator.local',
    );
    headers.putIfAbsent('X-Title', () => 'Argos Translate');
  }
  return headers;
}

String llmChatUrl(String baseUrl) => _llmEndpoint(baseUrl, 'chat/completions');

String llmCompletionsUrl(String baseUrl) =>
    _llmEndpoint(baseUrl, 'completions');

String llmModelsUrl(String baseUrl) => _llmEndpoint(baseUrl, 'models');

String _llmEndpoint(String baseUrl, String suffix) {
  final base = stripTrailingSlashes(baseUrl);
  if (base.endsWith('/v1')) {
    return '$base/$suffix';
  }
  return '$base/v1/$suffix';
}

String completionsPrompt(String systemPrompt, String userContent) =>
    '$systemPrompt\n\n### User:\n$userContent\n\n### Assistant:\n';
