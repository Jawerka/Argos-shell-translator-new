import 'dart:convert';

/// Разбивка UTF-8 байтового потока на строки (LF / CRLF).
Stream<String> utf8Lines(Stream<List<int>> bytes) async* {
  final buffer = StringBuffer();
  await for (final chunk in utf8.decoder.bind(bytes)) {
    buffer.write(chunk);
    var text = buffer.toString();
    while (true) {
      final idx = text.indexOf('\n');
      if (idx < 0) {
        break;
      }
      var line = text.substring(0, idx);
      if (line.endsWith('\r')) {
        line = line.substring(0, line.length - 1);
      }
      yield line;
      text = text.substring(idx + 1);
    }
    buffer
      ..clear()
      ..write(text);
  }
  if (buffer.isEmpty) {
    return;
  }
  var last = buffer.toString();
  if (last.endsWith('\r')) {
    last = last.substring(0, last.length - 1);
  }
  yield last;
}
