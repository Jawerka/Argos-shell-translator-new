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

/// Доля кириллицы, с которой AUTO считает текст русским.
const autoRuShare = 0.3;

/// Доля и минимум букв для поправки явной пары en/ru.
const explicitRuShare = 0.6;
const explicitMinLetters = 2;

final _fenceRe = RegExp(r'```.*?```', dotAll: true);
final _inlineCodeRe = RegExp(r'`[^`\n]+`');
final _urlRe = RegExp(r'https?://\S+|www\.\S+', caseSensitive: false);
final _emailRe = RegExp(r'\b[\w.+-]+@[\w.-]+\.\w+\b');
final _discordRe = RegExp(r'<@[!&]?\d+>|<#\d+>|<:[A-Za-z0-9_]+:\d+>');
final _emojiShortRe = RegExp(r':[A-Za-z0-9_]{2,}:');
final _letterRe = RegExp(r'\p{L}', unicode: true);
final _digitRe = RegExp(r'\p{N}', unicode: true);

/// Вердикт источника: `ru` или `other`, и можно ли развернуть явную пару.
class SourceVerdict {
  const SourceVerdict({
    required this.auto,
    required this.explicitFix,
    required this.cyr,
    required this.lat,
    required this.other,
    required this.share,
  });

  final String auto;
  final bool explicitFix;
  final int cyr;
  final int lat;
  final int other;
  final double share;

  /// `ru` / `en`, если источник однозначный для поправки пары en↔ru.
  String? get explicitSource {
    if (share >= explicitRuShare && cyr >= explicitMinLetters) {
      return 'ru';
    }
    if (cyr == 0 && lat >= explicitMinLetters) {
      return 'en';
    }
    return null;
  }
}

String _cleanLangText(String text) {
  var cleaned = text.replaceAll(_fenceRe, ' ');
  cleaned = cleaned.replaceAll(_inlineCodeRe, ' ');
  cleaned = cleaned.replaceAll(_urlRe, ' ');
  cleaned = cleaned.replaceAll(_emailRe, ' ');
  cleaned = cleaned.replaceAll(_discordRe, ' ');
  cleaned = cleaned.replaceAll(_emojiShortRe, ' ');
  return cleaned;
}

bool _isLetter(String ch) => _letterRe.hasMatch(ch);

bool _isDigit(String ch) => _digitRe.hasMatch(ch);

bool _isUpper(String ch) {
  final upper = ch.toUpperCase();
  final lower = ch.toLowerCase();
  return upper != lower && ch == upper;
}

String _script(String ch) {
  if (!_isLetter(ch)) {
    return '';
  }
  final code = ch.codeUnitAt(0);
  if ((code >= 0x0400 && code <= 0x052F) ||
      (code >= 0x1C80 && code <= 0x1C8F) ||
      (code >= 0x2DE0 && code <= 0x2DFF) ||
      (code >= 0xA640 && code <= 0xA69F)) {
    return 'cyr';
  }
  if ((code >= 0x41 && code <= 0x5A) ||
      (code >= 0x61 && code <= 0x7A) ||
      (code >= 0x00C0 && code <= 0x024F) ||
      (code >= 0x1E00 && code <= 0x1EFF)) {
    return 'lat';
  }
  return 'other';
}

bool _isWordChar(String ch) =>
    _isLetter(ch) || _isDigit(ch) || ch == '_' || ch == "'" || ch == '’';

bool _isSentenceMark(String ch) =>
    ch == '.' || ch == '!' || ch == '?' || ch == '…' || ch == '\n' || ch == '\r';

(int, int, int) _countToken(String token, bool sentenceStart) {
  var cyr = 0;
  var other = 0;
  final latin = <String>[];
  var hasDigitOrUnderscore = false;
  for (final rune in token.runes) {
    final ch = String.fromCharCodes([rune]);
    if (_isDigit(ch) || ch == '_') {
      hasDigitOrUnderscore = true;
      continue;
    }
    if (ch == "'" || ch == '’') {
      continue;
    }
    final script = _script(ch);
    if (script == 'cyr') {
      cyr += 1;
    } else if (script == 'lat') {
      latin.add(ch);
    } else if (script == 'other') {
      other += 1;
    }
  }
  var lat = 0;
  if (latin.isNotEmpty && !hasDigitOrUnderscore) {
    final uppers = latin.where(_isUpper).length;
    final internalUpper = latin.skip(1).any(_isUpper);
    final proper = _isUpper(latin.first) && !sentenceStart;
    final allCaps = uppers == latin.length && latin.length >= 2;
    if (!(allCaps || internalUpper || proper)) {
      lat = latin.length;
    }
  }
  return (cyr, lat, other);
}

SourceVerdict sourceVerdict(String text) {
  final cleaned = _cleanLangText(text);
  var cyr = 0;
  var lat = 0;
  var other = 0;
  var sentenceStart = true;
  final chars = [
    for (final rune in cleaned.runes) String.fromCharCodes([rune]),
  ];
  var i = 0;
  while (i < chars.length) {
    if (!_isWordChar(chars[i])) {
      if (_isSentenceMark(chars[i])) {
        sentenceStart = true;
      }
      i += 1;
      continue;
    }
    final start = i;
    while (i < chars.length && _isWordChar(chars[i])) {
      i += 1;
    }
    final counted = _countToken(chars.sublist(start, i).join(), sentenceStart);
    cyr += counted.$1;
    lat += counted.$2;
    other += counted.$3;
    sentenceStart = false;
  }
  final total = cyr + lat + other;
  final share = total == 0 ? 0.0 : cyr / total;
  final auto = total > 0 && share >= autoRuShare ? 'ru' : 'other';
  final draft = SourceVerdict(
    auto: auto,
    explicitFix: false,
    cyr: cyr,
    lat: lat,
    other: other,
    share: share,
  );
  return SourceVerdict(
    auto: auto,
    explicitFix: draft.explicitSource != null,
    cyr: cyr,
    lat: lat,
    other: other,
    share: share,
  );
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
