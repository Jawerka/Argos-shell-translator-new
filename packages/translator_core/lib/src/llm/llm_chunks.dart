import 'dart:math' as math;

import '../settings/app_settings.dart';
import '../text/text_utils.dart';
import 'llm_config.dart';

class LlmChunk {
  const LlmChunk({
    required this.translateText,
    this.joinBefore = '',
    this.contextText = '',
    this.splitLevel = 'paragraph',
    this.seamAfter = false,
    this.sourceStart = 0,
    this.sourceEnd = 0,
  });

  final String translateText;
  final String joinBefore;
  final String contextText;
  final String splitLevel;
  final bool seamAfter;
  final int sourceStart;
  final int sourceEnd;
}

class _Segment {
  const _Segment({
    required this.text,
    required this.joinBefore,
    required this.level,
    required this.start,
    required this.end,
  });

  final String text;
  final String joinBefore;
  final String level;
  final int start;
  final int end;
}

List<(int, int)> _paragraphRanges(String text) {
  final ranges = <(int, int)>[];
  final n = text.length;
  var i = 0;
  while (i < n) {
    while (i < n && text[i] == '\n') {
      i += 1;
    }
    if (i >= n) {
      break;
    }
    final start = i;
    while (i < n) {
      if (i + 1 < n && text[i] == '\n' && text[i + 1] == '\n') {
        break;
      }
      i += 1;
    }
    ranges.add((start, i));
    while (i < n && text[i] == '\n') {
      i += 1;
    }
  }
  if (ranges.isEmpty && text.isNotEmpty) {
    ranges.add((0, n));
  }
  return ranges;
}

List<(String, String)> _splitOversizedText(String block, int maxChars) {
  if (block.length <= maxChars) {
    return [(block, 'paragraph')];
  }
  final sentences = splitParagraphIntoSentences(block);
  if (sentences.isEmpty) {
    return [(block, 'word')];
  }
  if (sentences.length == 1 && block.length > maxChars) {
    return [
      for (final part in fallbackSplitByWords(block))
        if (part.trim().isNotEmpty) (part, 'word'),
    ];
  }
  final parts = <(String, String)>[];
  for (final (start, end) in makeSentenceChunks(
    sentences,
    maxChars: maxChars,
    overlap: 0,
  )) {
    final chunk = sentences.sublist(start, end).join(' ');
    if (chunk.trim().isNotEmpty) {
      parts.add((chunk, 'sentence'));
    }
  }
  return parts.isEmpty ? [(block, 'paragraph')] : parts;
}

int _findInRange(String text, String sub, int start, int end) {
  if (start >= end || start >= text.length || sub.isEmpty) {
    return -1;
  }
  final stop = math.min(end, text.length);
  final rel = text.substring(start, stop).indexOf(sub);
  if (rel < 0) {
    return -1;
  }
  return start + rel;
}

List<_Segment> _textToSegments(String text, int maxChars) {
  final segments = <_Segment>[];
  final ranges = _paragraphRanges(text);
  if (ranges.isEmpty) {
    if (text.isNotEmpty) {
      segments.add(
        _Segment(
          text: text,
          joinBefore: '',
          level: 'paragraph',
          start: 0,
          end: text.length,
        ),
      );
    }
    return segments;
  }

  for (var paraIdx = 0; paraIdx < ranges.length; paraIdx++) {
    final (start, end) = ranges[paraIdx];
    final paraText = text.substring(start, end);
    final join = paraIdx > 0 ? '\n\n' : '';
    if (paraText.length <= maxChars) {
      segments.add(
        _Segment(
          text: paraText,
          joinBefore: join,
          level: 'paragraph',
          start: start,
          end: end,
        ),
      );
      continue;
    }

    final subparts = _splitOversizedText(paraText, maxChars);
    var offset = start;
    for (var subIdx = 0; subIdx < subparts.length; subIdx++) {
      final (subText, level) = subparts[subIdx];
      final subJoin = subIdx == 0 ? join : (level == 'sentence' ? '\n' : ' ');
      var subStart = _findInRange(text, subText, offset, end);
      if (subStart < 0) {
        subStart = offset;
      }
      final subEnd = subStart + subText.length;
      segments.add(
        _Segment(
          text: subText,
          joinBefore: subJoin,
          level: level,
          start: subStart,
          end: subEnd,
        ),
      );
      offset = subEnd;
    }
  }
  return segments;
}

List<List<_Segment>> _packSegments(List<_Segment> segments, int maxChars) {
  if (segments.isEmpty) {
    return const [];
  }
  final packs = <List<_Segment>>[];
  var current = <_Segment>[];
  var currentLen = 0;

  for (final seg in segments) {
    final addLen =
        seg.text.length + (current.isEmpty ? 0 : seg.joinBefore.length);
    if (current.isNotEmpty && currentLen + addLen > maxChars) {
      packs.add(current);
      current = [seg];
      currentLen = seg.text.length;
    } else {
      current.add(seg);
      currentLen += addLen;
    }
  }
  if (current.isNotEmpty) {
    packs.add(current);
  }
  return packs;
}

LlmChunk _segmentsToChunk(List<_Segment> pack) {
  final translate = StringBuffer();
  for (final seg in pack) {
    translate.write(seg.joinBefore);
    translate.write(seg.text);
  }
  const levelOrder = {'paragraph': 0, 'sentence': 1, 'word': 2};
  var level = 'paragraph';
  var best = -1;
  for (final seg in pack) {
    final order = levelOrder[seg.level] ?? 0;
    if (order > best) {
      best = order;
      level = seg.level;
    }
  }
  return LlmChunk(
    translateText: translate.toString(),
    joinBefore: '',
    splitLevel: level,
    seamAfter: level != 'paragraph',
    sourceStart: pack.isEmpty ? 0 : pack.first.start,
    sourceEnd: pack.isEmpty ? 0 : pack.last.end,
  );
}

/// Disjoint-разбиение: абзацы → предложения → слова.
List<LlmChunk> splitLlmChunks(String text, int maxChars) {
  if (text.isEmpty) {
    return const [LlmChunk(translateText: '', sourceStart: 0, sourceEnd: 0)];
  }
  if (text.length <= maxChars) {
    return [
      LlmChunk(
        translateText: text,
        sourceStart: 0,
        sourceEnd: text.length,
      ),
    ];
  }

  final segments = _textToSegments(text, maxChars);
  final packs = _packSegments(segments, maxChars);
  final chunks = <LlmChunk>[];
  for (var idx = 0; idx < packs.length; idx++) {
    final base = _segmentsToChunk(packs[idx]);
    var context = '';
    if (idx > 0) {
      final prevPack = packs[idx - 1];
      final contextParts = [prevPack.last.text];
      if (prevPack.length > 1 &&
          prevPack[prevPack.length - 2].level == 'paragraph') {
        contextParts.insert(0, prevPack[prevPack.length - 2].text);
      }
      context = contextParts.join('\n\n');
    }
    chunks.add(
      LlmChunk(
        translateText: base.translateText,
        joinBefore: base.joinBefore,
        contextText: context,
        splitLevel: base.splitLevel,
        seamAfter: base.seamAfter,
        sourceStart: base.sourceStart,
        sourceEnd: base.sourceEnd,
      ),
    );
  }
  return chunks;
}

int chunkMaxChars(LlmSettings llm, String? fileType) {
  if (fileType != null) {
    return math.max(500, llm.fileChunkMaxChars);
  }
  return math.max(500, llm.chunkMaxChars);
}

int adaptiveMaxTokens(int textLen, int baseMax, {bool fileMode = false}) {
  final cap = fileMode ? 2048 : 8192;
  final estimated = (textLen / 2.5).toInt() + 256;
  if (fileMode) {
    return math.min(cap, math.min(baseMax, math.max(512, estimated)));
  }
  return math.min(cap, math.max(baseMax, estimated));
}

double adaptiveChunkTimeout(
  int textLen,
  int baseTimeout, {
  bool fileMode = false,
}) {
  final divisor = fileMode ? 8 : 30;
  return math.max(baseTimeout, textLen ~/ divisor).toDouble();
}

String translatedTail(String text, {int maxChars = llmContextTailChars}) {
  final stripped = text.trimRight();
  if (stripped.length <= maxChars) {
    return stripped;
  }
  final tail = stripped.substring(stripped.length - maxChars);
  final space = tail.indexOf(' ');
  if (space > 0) {
    return tail.substring(space + 1);
  }
  return tail;
}

String stripLeadingContextRepeat(String output, String translatedTailText) {
  if (translatedTailText.isEmpty || output.length < llmStripPrefixMin) {
    return output;
  }
  final take = math.min(200, translatedTailText.length);
  final check = translatedTailText.substring(translatedTailText.length - take);
  if (check.length >= llmStripPrefixMin && output.startsWith(check)) {
    final stripped = output.substring(check.length).trimLeft();
    if (stripped.trim().isNotEmpty) {
      return stripped;
    }
  }
  return output;
}

String buildChunkUserContent({
  required LlmChunk chunk,
  required int chunkIndex,
  required int total,
  String? fileType,
  required String translatedTailText,
  required bool useContext,
}) {
  final parts = <String>[];
  if (fileType != null && chunkIndex == 0) {
    parts.add('File type: $fileType');
  }
  if (chunkIndex > 0 && useContext) {
    parts.add('Document part ${chunkIndex + 1}/$total.');
    if (chunk.contextText.isNotEmpty) {
      parts.add(
        'Context from previous source (for continuity only, do not translate again):\n---\n'
        '${chunk.contextText}\n---',
      );
    }
    if (translatedTailText.isNotEmpty) {
      parts.add(
        'Previous translation ended with:\n---\n'
        '$translatedTailText\n---',
      );
    }
    parts.add(
      'Translate the following segment. Output ONLY the translation of the new segment:\n---\n'
      '${chunk.translateText}\n---',
    );
  } else {
    parts.add(chunk.translateText);
  }
  return parts.join('\n\n');
}

String joinChunkOutputs(List<String> parts) => parts.join();
