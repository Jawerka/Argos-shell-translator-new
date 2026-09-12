import 'dart:convert';

import 'package:test/test.dart';
import 'package:translator_core/translator_core.dart';

void main() {
  test('utf8Lines splits LF, CRLF and a tail without newline', () async {
    final bytes = Stream<List<int>>.fromIterable([
      utf8.encode('one\r\n'),
      utf8.encode('tw'),
      utf8.encode('o\nlast'),
    ]);
    expect(await utf8Lines(bytes).toList(), ['one', 'two', 'last']);
  });

  test('utf8Lines yields empty for empty stream', () async {
    expect(await utf8Lines(const Stream<List<int>>.empty()).toList(), isEmpty);
  });
}
