import 'package:flutter_test/flutter_test.dart';
import 'package:translator/features/session/argos_assembler.dart';
import 'package:translator/features/session/language_swap.dart';

void main() {
  test('AUTO swap keeps auto and uses detected target', () {
    final next = swapLanguagePair(
      langFrom: 'auto',
      langTo: 'ru',
      detectedLang: 'en',
    );
    expect(next.from, 'auto');
    expect(next.to, 'en');
  });

  test('AUTO swap toggles ru/en when detected is missing', () {
    final next = swapLanguagePair(
      langFrom: 'auto',
      langTo: 'ru',
    );
    expect(next.from, 'auto');
    expect(next.to, 'en');
  });

  test('explicit pair swaps both sides', () {
    final next = swapLanguagePair(langFrom: 'en', langTo: 'ru');
    expect(next.from, 'ru');
    expect(next.to, 'en');
  });

  test('argos assembler joins chunks by paragraph', () {
    final assembler = ArgosAssembler();
    assembler.reset(3);
    assembler.put(index: 0, paraIdx: 0, text: 'Hello');
    assembler.put(index: 1, paraIdx: 0, text: 'world');
    assembler.put(index: 2, paraIdx: 1, text: 'Next');
    expect(assembler.assemble(), 'Hello world\n\nNext');
  });

  test('hasParagraphAnchors is true when paraIdx present', () {
    final assembler = ArgosAssembler();
    expect(assembler.hasParagraphAnchors, isFalse);
    assembler.put(index: 0, paraIdx: 0, text: 'a');
    expect(assembler.hasParagraphAnchors, isTrue);
  });

  test('paragraphStartOffsets splits on blank lines', () {
    expect(paragraphStartOffsets(''), const [0]);
    expect(paragraphStartOffsets('one'), const [0]);
    expect(paragraphStartOffsets('one\n\ntwo'), const [0, 5]);
    expect(paragraphStartOffsets('a\n\nb\n\nc'), const [0, 3, 6]);
  });
}
