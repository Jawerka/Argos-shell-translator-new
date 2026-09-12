import 'package:test/test.dart';
import 'package:translator_core/translator_core.dart';

void main() {
    test('resolveAutoPair table', () {
      expect(resolveAutoPair('ru', 'ru'), (from: 'ru', to: 'en'));
      expect(resolveAutoPair('en', 'ru'), (from: 'en', to: 'ru'));
      expect(resolveAutoPair('de', 'ru'), (from: 'de', to: 'ru'));
      expect(resolveAutoPair('de', 'de'), (from: 'de', to: 'ru'));
      expect(resolveAutoPair('', 'ru'), (from: 'en', to: 'ru'));
      expect(resolveAutoPair('en', ''), (from: 'en', to: 'ru'));
      expect(resolveAutoPair('  RU ', ' ru'), (from: 'ru', to: 'en'));
    });

    test('snapDetectedLang table', () {
      const installed = ['en->ru', 'ru->en'];
      expect(
        snapDetectedLang('nl', hasCyrillic: false, installedFromCodes: installed),
        'en',
      );
      expect(
        snapDetectedLang('ca', hasCyrillic: false, installedFromCodes: installed),
        'en',
      );
      expect(
        snapDetectedLang('bg', hasCyrillic: true, installedFromCodes: installed),
        'ru',
      );
      expect(
        snapDetectedLang(
          'nl',
          hasCyrillic: false,
          installedFromCodes: const ['en-ru'],
        ),
        'en',
      );
      expect(
        snapDetectedLang(
          'de',
          hasCyrillic: false,
          installedFromCodes: const ['en->ru', 'de->ru'],
        ),
        'de',
      );
      expect(snapDetectedLang('en', hasCyrillic: false), 'en');
      expect(snapDetectedLang('', hasCyrillic: true), 'ru');
    });
}
