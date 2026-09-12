import 'dart:math';

/// Сборка текста Argos из чанков по index/para_idx (как CTk set_argos_text).
class ArgosAssembler {
  final Map<int, ({String text, int paraIdx})> _chunks = {};
  int total = 0;

  void reset(int unitCount) {
    _chunks.clear();
    total = unitCount;
  }

  void put({required int index, required int paraIdx, required String text}) {
    _chunks[index] = (text: text, paraIdx: paraIdx);
  }

  bool get hasParagraphAnchors =>
      _chunks.values.any((chunk) => chunk.paraIdx >= 0) && _chunks.isNotEmpty;

  String assemble() {
    if (total <= 0 && _chunks.isEmpty) {
      return '';
    }
    final count = total > 0 ? total : (_chunks.keys.reduce(max) + 1);

    final paraBlocks = <int, List<String>>{};
    var lastPara = 0;
    for (var i = 0; i < count; i++) {
      final entry = _chunks[i];
      if (entry != null) {
        paraBlocks.putIfAbsent(entry.paraIdx, () => <String>[]).add(entry.text);
        lastPara = entry.paraIdx;
      } else {
        paraBlocks.putIfAbsent(lastPara, () => <String>[]).add('');
      }
    }
    if (paraBlocks.isEmpty) {
      return '';
    }

    final maxIdx = paraBlocks.keys.reduce(max);
    final out = <String>[];
    for (var paraIdx = 0; paraIdx <= maxIdx; paraIdx++) {
      final sents = paraBlocks[paraIdx] ?? const <String>[];
      final nonEmpty = sents.where((s) => s.isNotEmpty).toList();
      if (nonEmpty.isNotEmpty) {
        out.add(nonEmpty.join(' '));
      }
    }
    return out.join('\n\n');
  }
}

/// Начала абзацев (разделитель — две и больше новых строк) в символах.
List<int> paragraphStartOffsets(String text) {
  if (text.isEmpty) {
    return const <int>[0];
  }
  final paras = text.split(RegExp(r'\n{2,}'));
  final offsets = <int>[];
  var cumulative = 0;
  for (final para in paras) {
    offsets.add(cumulative);
    cumulative += para.length + 2;
  }
  return offsets;
}
