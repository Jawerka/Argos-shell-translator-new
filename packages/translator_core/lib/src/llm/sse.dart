import 'dart:convert';

import '../json_util.dart';

String _normalizeContentField(Object? value) {
  if (value == null) {
    return '';
  }
  if (value is String) {
    return value;
  }
  if (value is List) {
    final parts = <String>[];
    for (final item in value) {
      if (item is Map) {
        final part = item['text'] ?? item['content'];
        if (part != null && '$part'.isNotEmpty) {
          parts.add('$part');
        }
      } else if (item != null && '$item'.isNotEmpty) {
        parts.add('$item');
      }
    }
    return parts.join();
  }
  return '$value';
}

/// Из SSE-строки: (content_delta, reasoning_delta).
(String, String) parseSseParts(String line) {
  if (!line.startsWith('data:')) {
    return ('', '');
  }
  final payload = line.substring(5).trim();
  if (payload == '[DONE]') {
    return ('', '');
  }
  late final Map<String, dynamic> data;
  try {
    final decoded = jsonDecode(payload);
    if (decoded is! Map) {
      return ('', '');
    }
    data = asStringKeyedMap(decoded);
  } on FormatException {
    return ('', '');
  }
  final choices = data['choices'];
  if (choices is! List || choices.isEmpty) {
    return ('', '');
  }
  final choiceRaw = choices.first;
  if (choiceRaw is! Map) {
    return ('', '');
  }
  final choice = asStringKeyedMap(choiceRaw);
  final deltaRaw = choice['delta'];
  final delta =
      deltaRaw is Map ? asStringKeyedMap(deltaRaw) : <String, dynamic>{};

  var content = _normalizeContentField(delta['content']);
  if (content.isEmpty) {
    content = _normalizeContentField(delta['text']);
  }
  if (content.isEmpty) {
    content = _normalizeContentField(choice['text']);
  }

  var reasoning = _normalizeContentField(delta['reasoning_content']);
  final messageRaw = choice['message'];
  final message =
      messageRaw is Map ? asStringKeyedMap(messageRaw) : <String, dynamic>{};
  if (content.isEmpty) {
    content = _normalizeContentField(message['content']);
  }
  if (reasoning.isEmpty) {
    reasoning = _normalizeContentField(message['reasoning_content']);
  }
  return (content, reasoning);
}

String? parseSseErrorMessage(String line) {
  if (!line.startsWith('data:')) {
    return null;
  }
  final payload = line.substring(5).trim();
  if (payload.isEmpty || payload == '[DONE]') {
    return null;
  }
  try {
    final decoded = jsonDecode(payload);
    if (decoded is! Map) {
      return null;
    }
    final data = asStringKeyedMap(decoded);
    final error = data['error'];
    if (error == null) {
      return null;
    }
    if (error is String && error.trim().isNotEmpty) {
      return error.trim();
    }
    if (error is Map) {
      final mapped = asStringKeyedMap(error);
      final message = mapped['message'] ?? mapped['msg'] ?? mapped['code'];
      if (message != null && '$message'.trim().isNotEmpty) {
        return '$message'.trim();
      }
    }
    final asText = '$error'.trim();
    return asText.isEmpty ? 'LLM stream error' : asText;
  } on FormatException {
    return null;
  }
}

String? parseSseToken(String line) {
  final (content, reasoning) = parseSseParts(line);
  final piece = content.isNotEmpty ? content : reasoning;
  return piece.isEmpty ? null : piece;
}

/// Qwen может отдать весь ответ только в reasoning_content.
String finalizeStreamText(String content, String reasoning) {
  if (content.trim().isNotEmpty) {
    return content;
  }
  if (reasoning.trim().isNotEmpty) {
    return reasoning;
  }
  return '';
}

bool shouldFallbackToCompletions(int statusCode, String responseText) {
  if (statusCode != 404 && statusCode != 405) {
    return false;
  }
  final lower = responseText.toLowerCase();
  if (lower.contains('model') &&
      lower.contains('not found') &&
      !lower.contains('chat')) {
    return false;
  }
  return true;
}

String extractNonStreamContent(Map<String, dynamic> data) {
  final choices = data['choices'];
  if (choices is! List || choices.isEmpty) {
    return '';
  }
  final choiceRaw = choices.first;
  if (choiceRaw is! Map) {
    return '';
  }
  final choice = asStringKeyedMap(choiceRaw);
  final messageRaw = choice['message'];
  final message =
      messageRaw is Map ? asStringKeyedMap(messageRaw) : <String, dynamic>{};
  final content = _normalizeContentField(message['content']);
  if (content.trim().isNotEmpty) {
    return content;
  }
  final reasoning = _normalizeContentField(message['reasoning_content']);
  if (reasoning.trim().isNotEmpty) {
    return reasoning;
  }
  return _normalizeContentField(choice['text']);
}
