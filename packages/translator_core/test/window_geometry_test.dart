import 'package:test/test.dart';
import 'package:translator_core/translator_core.dart';

void main() {
  test('keeps on-screen bounds and enforces min 800x600', () {
    const ok = WindowGeometry(left: 120, top: 80, width: 1000, height: 700);
    final clamped = ok.clampToVisible();
    expect(clamped.left, 120);
    expect(clamped.top, 80);
    expect(clamped.width, 1000);
    expect(clamped.height, 700);

    const tiny = WindowGeometry(left: 10, top: 20, width: 100, height: 100);
    final grown = tiny.clampToVisible();
    expect(grown.width, WindowGeometry.minWidth);
    expect(grown.height, WindowGeometry.minHeight);
    expect(grown.left, 10);
    expect(grown.top, 20);
  });

  test('pulls wildly off-screen origin back', () {
    const farLeft = WindowGeometry(
      left: -10000,
      top: 50,
      width: 1000,
      height: 700,
    );
    expect(farLeft.clampToVisible().left, 40);

    const farUp = WindowGeometry(
      left: 80,
      top: -200,
      width: 1000,
      height: 700,
    );
    expect(farUp.clampToVisible().top, 40);

    const farRight = WindowGeometry(
      left: 9000,
      top: 50,
      width: 1000,
      height: 700,
    );
    expect(farRight.clampToVisible().left, 40);

    const farDown = WindowGeometry(
      left: 80,
      top: 8000,
      width: 1000,
      height: 700,
    );
    expect(farDown.clampToVisible().top, 40);
  });
}
