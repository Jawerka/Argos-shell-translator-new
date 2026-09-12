import 'package:flutter_test/flutter_test.dart';
import 'package:translator/platform/triple_copy.dart';

void main() {
  test('TripleCopyDetector fires on third press in window when sequence changes',
      () {
    final detector = TripleCopyDetector(windowMs: 600);
    expect(detector.registerPress(nowMs: 0, sequence: 1), isFalse);
    expect(detector.registerPress(nowMs: 100, sequence: 2), isFalse);
    expect(detector.registerPress(nowMs: 200, sequence: 3), isTrue);
  });

  test('TripleCopyDetector ignores three presses with unchanged sequence', () {
    final detector = TripleCopyDetector(windowMs: 600);
    expect(detector.registerPress(nowMs: 0, sequence: 4), isFalse);
    expect(detector.registerPress(nowMs: 50, sequence: 4), isFalse);
    expect(detector.registerPress(nowMs: 100, sequence: 4), isFalse);
  });

  test('TripleCopyDetector resets after window expires', () {
    final detector = TripleCopyDetector(windowMs: 600);
    expect(detector.registerPress(nowMs: 0, sequence: 1), isFalse);
    expect(detector.registerPress(nowMs: 100, sequence: 2), isFalse);
    expect(detector.registerPress(nowMs: 800, sequence: 3), isFalse);
    expect(detector.registerPress(nowMs: 850, sequence: 4), isFalse);
    expect(detector.registerPress(nowMs: 900, sequence: 5), isTrue);
  });

  test('clipboardSequenceChanged', () {
    expect(clipboardSequenceChanged(before: 1, after: 2), isTrue);
    expect(clipboardSequenceChanged(before: 3, after: 3), isFalse);
  });
}
