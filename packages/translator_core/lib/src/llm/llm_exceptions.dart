class LlmDisabledException implements Exception {
  @override
  String toString() => 'LLM отключён';
}

class LlmConfigException implements Exception {
  LlmConfigException(this.message);

  final String message;

  @override
  String toString() => message;
}

class LlmCancelledException implements Exception {
  LlmCancelledException([this.message = 'LLM: запрос отменён']);

  final String message;

  @override
  String toString() => message;
}

class LlmException implements Exception {
  LlmException(this.message);

  final String message;

  @override
  String toString() => message;
}

class LlmHttpException implements Exception {
  LlmHttpException(this.statusCode, this.body);

  final int statusCode;
  final String body;

  @override
  String toString() => 'HTTP $statusCode';
}
