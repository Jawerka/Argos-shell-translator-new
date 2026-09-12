import 'package:flutter_test/flutter_test.dart';
import 'package:translator/features/session/scroll_sync.dart';

void main() {
  test('paragraphIndexForRatio picks nearest start', () {
    const starts = [0, 10, 25];
    expect(paragraphIndexForRatio(starts, 40, 0), 0);
    expect(paragraphIndexForRatio(starts, 40, 0.3), 1);
    expect(paragraphIndexForRatio(starts, 40, 0.9), 2);
    expect(paragraphIndexForRatio(const [], 10, 0.5), 0);
  });

  test('ratioForParagraph maps paragraph to scroll ratio', () {
    const starts = [0, 10, 25];
    expect(ratioForParagraph(starts, 40, 0), 0);
    expect(ratioForParagraph(starts, 40, 1), closeTo(10 / 40, 1e-9));
    expect(ratioForParagraph(starts, 40, 2), closeTo(25 / 40, 1e-9));
    expect(ratioForParagraph(starts, 40, 99), 1);
    expect(ratioForParagraph(const [], 40, 0), 0);
  });
}
