import 'package:test/test.dart';
import 'package:translator_core/translator_core.dart';

void main() {
  test('copyWith changes streaming without mutating original', () {
    const original = AppSettings(streaming: true, scrollSync: true);
    final copy = original.copyWith(streaming: false);
    expect(original.streaming, isTrue);
    expect(copy.streaming, isFalse);
    expect(copy.scrollSync, isTrue);
  });

  test('copyWith copies nested llm maps', () {
    const original = AppSettings();
    final copy = original.copyWith();
    copy.llm.apiKeys['openrouter'] = 'mutated';
    copy.llm.providerUrls['local'] = 'http://example.invalid/v1';
    expect(original.llm.apiKeys['openrouter'], isEmpty);
    expect(original.llm.providerUrls['local'], isEmpty);
  });
}
