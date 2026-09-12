// Разбивка текста на абзацы, предложения и fenced-блоки (порт text_utils.py).

const maxCharsPerChunk = 4000;
const sentenceWindow = 1;

final sentenceRegex = RegExp(
  '(?<=\\S[.!?…])\\s+(?=[A-ZА-ЯЁ0-9"\'«])',
);
final codeFenceRegex = RegExp(
  r'```[^\n]*\n.*?```',
  dotAll: true,
);

/// Сегменты: (фрагмент, translatable). False = fenced code block.
List<(String, bool)> splitProseAndCodeFences(String text) {
  if (text.isEmpty) {
    return const [];
  }
  final segments = <(String, bool)>[];
  var pos = 0;
  for (final match in codeFenceRegex.allMatches(text)) {
    if (match.start > pos) {
      segments.add((text.substring(pos, match.start), true));
    }
    segments.add((match.group(0)!, false));
    pos = match.end;
  }
  if (pos < text.length) {
    segments.add((text.substring(pos), true));
  }
  if (segments.isEmpty) {
    segments.add((text, true));
  }
  return segments;
}

List<String> splitIntoParagraphs(String text) {
  if (text.trim().isEmpty) {
    return const [];
  }
  return [
    for (final part in text.split(RegExp(r'\n{2,}')))
      if (part.trim().isNotEmpty) part.trim(),
  ];
}

List<String> splitParagraphIntoSentences(String paragraph) {
  final trimmed = paragraph.trim();
  if (trimmed.isEmpty) {
    return const [];
  }
  late final List<String> sentences;
  try {
    sentences = trimmed.split(sentenceRegex);
  } on Object {
    sentences = [trimmed];
  }
  if (sentences.length == 1 && trimmed.length > maxCharsPerChunk) {
    return fallbackSplitByWords(trimmed);
  }
  return [
    for (final sentence in sentences)
      if (sentence.trim().isNotEmpty) sentence.trim(),
  ];
}

List<String> fallbackSplitByWords(
  String text, {
  int maxChars = maxCharsPerChunk,
}) {
  final words = [
    for (final word in text.split(RegExp(r'\s+')))
      if (word.isNotEmpty) word,
  ];
  final chunks = <String>[];
  final current = <String>[];
  var currentLen = 0;

  for (final word in words) {
    current.add(word);
    currentLen += word.length + 1;
    if (currentLen >= maxChars) {
      chunks.add(current.join(' '));
      current.clear();
      currentLen = 0;
    }
  }
  if (current.isNotEmpty) {
    chunks.add(current.join(' '));
  }
  return chunks;
}

/// Диапазоны [start, end) индексов предложений.
List<(int, int)> makeSentenceChunks(
  List<String> sentences, {
  int maxChars = maxCharsPerChunk,
  int overlap = sentenceWindow,
}) {
  if (sentences.isEmpty) {
    return const [];
  }
  final ranges = <(int, int)>[];
  final n = sentences.length;
  var i = 0;
  while (i < n) {
    var curLen = 0;
    var j = i;
    while (j < n && (curLen + sentences[j].length + 1) <= maxChars) {
      curLen += sentences[j].length + 1;
      j += 1;
    }
    if (j == i) {
      j = i + 1;
    }
    ranges.add((i, j));
    if (j >= n) {
      break;
    }
    // Как в Python: i = max(j - overlap, j) — при overlap ≥ 0 это j.
    i = (j - overlap) > j ? (j - overlap) : j;
  }
  return ranges;
}

/// Простая эвристика для UI, без langdetect.
String detectLanguageHeuristic(String text) {
  final trimmed = text.trim();
  if (trimmed.isEmpty) {
    return 'en';
  }
  if (RegExp(r'[А-Яа-яЁё]').hasMatch(trimmed)) {
    return 'ru';
  }
  return 'en';
}
