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

final cyrillicRegex = RegExp(r'[А-Яа-яЁё]');
const cyrillicLangs = {'ru', 'bg', 'uk', 'mk', 'sr', 'be', 'kk'};
const defaultFromCodes = {'en', 'ru'};

bool containsCyrillic(String text) => cyrillicRegex.hasMatch(text);

/// Исходные коды из пар `en->ru` / `en-ru` или уже готовые `en`.
Set<String> installedFromCodesFromPairs(Iterable<Object?> pairs) {
  final out = <String>{};
  for (final raw in pairs) {
    if (raw == null) {
      continue;
    }
    var item = raw.toString().trim().toLowerCase().replaceAll('→', '->');
    if (item.isEmpty) {
      continue;
    }
    if (item.contains('->')) {
      item = item.split('->').first.trim();
    } else if (item.contains('-')) {
      item = item.split('-').first.trim();
    }
    if (item.isNotEmpty) {
      out.add(item);
    }
  }
  return out;
}

/// Простая эвристика для UI, без Lingua (детект — в sidecar).
String detectLanguageHeuristic(String text) {
  final trimmed = text.trim();
  if (trimmed.isEmpty) {
    return 'en';
  }
  if (containsCyrillic(trimmed)) {
    return 'ru';
  }
  return 'en';
}

/// Первые [n] слов для диагностического лога (длинные слова обрезаются).
String peekWords(String text, {int n = 3, int maxWordLen = 24}) {
  final trimmed = text.trim();
  if (trimmed.isEmpty) {
    return '';
  }
  final words = <String>[];
  for (final match in RegExp(r'\S+').allMatches(trimmed)) {
    var word = match.group(0)!;
    if (word.length > maxWordLen) {
      word = '${word.substring(0, maxWordLen)}…';
    }
    words.add(word);
    if (words.length >= n) {
      break;
    }
  }
  return words.join(' ');
}

/// Свести детект к установленным from-кодам, иначе en/ru по алфавиту.
String snapDetectedLang(
  String detected, {
  required bool hasCyrillic,
  Iterable<Object?> installedFromCodes = const [],
}) {
  final heuristic = hasCyrillic ? 'ru' : 'en';
  final code = detected.trim().toLowerCase();
  if (code.isEmpty || code == 'auto') {
    return heuristic;
  }
  var installed = installedFromCodesFromPairs(installedFromCodes);
  if (installed.isEmpty) {
    installed = {...defaultFromCodes};
  }
  if (hasCyrillic && !cyrillicLangs.contains(code)) {
    return installed.contains('ru') ? 'ru' : heuristic;
  }
  if (!hasCyrillic && cyrillicLangs.contains(code)) {
    return installed.contains('en') ? 'en' : heuristic;
  }
  if (installed.contains(code)) {
    return code;
  }
  return heuristic;
}

/// AUTO: предпочтительная цель; при совпадении с детектом — переворот ru↔en.
({String from, String to}) resolveAutoPair(
  String detected,
  String preferredTo,
) {
  final from = detected.trim().toLowerCase().isEmpty
      ? 'en'
      : detected.trim().toLowerCase();
  final preferred = preferredTo.trim().toLowerCase().isEmpty
      ? 'ru'
      : preferredTo.trim().toLowerCase();
  if (from == preferred) {
    return (from: from, to: from == 'ru' ? 'en' : 'ru');
  }
  return (from: from, to: preferred);
}
