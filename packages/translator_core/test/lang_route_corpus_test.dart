import 'dart:convert';
import 'dart:io';

import 'package:test/test.dart';
import 'package:translator_core/translator_core.dart';

File _corpusFile() {
  var dir = Directory.current;
  for (var i = 0; i < 5; i++) {
    final file = File('${dir.path}/tests/fixtures/lang_route/corpus.json');
    if (file.existsSync()) {
      return file;
    }
    final parent = dir.parent;
    if (parent.path == dir.path) {
      break;
    }
    dir = parent;
  }
  throw StateError('corpus.json not found from ${Directory.current.path}');
}

void main() {
  final rows = (jsonDecode(_corpusFile().readAsStringSync()) as List<dynamic>)
      .cast<Map<String, dynamic>>();

  test('corpus auto and explicit_fix', () {
    final failures = <String>[];
    for (final row in rows) {
      final verdict = sourceVerdict(row['text'] as String);
      if (verdict.auto != row['auto'] ||
          verdict.explicitFix != row['explicit_fix']) {
        failures.add(
          '${row['id']} auto=${verdict.auto}/${row['auto']} '
          'fix=${verdict.explicitFix}/${row['explicit_fix']} '
          'cyr=${verdict.cyr} lat=${verdict.lat} share=${verdict.share.toStringAsFixed(2)}',
        );
      }
    }
    if (failures.isNotEmpty) {
      // ignore: avoid_print
      print('lang route corpus failed: ${failures.join(', ')}');
    }
    expect(failures, isEmpty);
  });

  test('log replay gives the final pair without swaps', () {
    final failures = <String>[];
    for (final row in rows) {
      if (row['origin'] != 'log') {
        continue;
      }
      final verdict = sourceVerdict(row['text'] as String);
      final pair = verdict.auto == 'ru' ? ('ru', 'en') : ('en', 'ru');
      final expected = row['auto'] == 'ru' ? ('ru', 'en') : ('en', 'ru');
      if (pair != expected) {
        failures.add(row['id'] as String);
      }
    }
    if (failures.isNotEmpty) {
      // ignore: avoid_print
      print('lang route replay failed: ${failures.join(', ')}');
    }
    expect(failures, isEmpty);
  });

  test('anchor counts match Python', () {
    final cases = <String, (int, int, int, String, bool)>{
      'Эти два?': (6, 0, 0, 'ru', true),
      'knee_together': (0, 0, 0, 'other', false),
      'The word гардиент means gradient in my notes': (8, 29, 0, 'other', false),
      'Запусти docker compose up и посмотри logs в Grafana': (17, 19, 0, 'ru', false),
      'OK': (0, 0, 0, 'other', false),
      'Да': (2, 0, 0, 'ru', true),
    };
    cases.forEach((text, expected) {
      final verdict = sourceVerdict(text);
      expect(
        (verdict.cyr, verdict.lat, verdict.other, verdict.auto, verdict.explicitFix),
        expected,
        reason: text,
      );
    });
  });
}
