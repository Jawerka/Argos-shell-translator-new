import 'dart:convert';
import 'dart:io';

import 'package:translator_core/translator_core.dart';

const textFileExtensions = <String>[
  'txt',
  'md',
  'markdown',
  'csv',
  'json',
  'xml',
  'html',
  'htm',
  'yaml',
  'yml',
  'ini',
  'cfg',
  'log',
  'rst',
  'toml',
];

bool isOpenableDocument(String path) => isSupportedTextPath(path);

String suggestedTranslationPath(
  String src, {
  required String suffix,
  required String engine,
}) {
  return suggestOutputPath(src, suffix: suffix, engine: engine);
}

/// Как Python `resolve_output_encoding`.
String resolveOutputEncoding(String? sourceEncoding, String outputMode) {
  final mode = outputMode.trim().toLowerCase();
  if (mode == 'utf-8' || mode == 'utf-8-sig') {
    return mode;
  }
  final src = (sourceEncoding ?? 'utf-8').trim().toLowerCase();
  if (src.isEmpty || src == 'utf-8-sig') {
    return 'utf-8';
  }
  return src;
}

bool exceedsLargeFileWarn(int charCount, int warnChars) =>
    charCount > warnChars;

Future<void> writeEncodedTextFile({
  required String path,
  required String content,
  required String encoding,
}) async {
  final file = File(path);
  await file.parent.create(recursive: true);
  if (encoding == 'utf-8-sig') {
    await file.writeAsBytes(<int>[
      0xEF,
      0xBB,
      0xBF,
      ...utf8.encode(content),
    ]);
    return;
  }
  await file.writeAsString(content, encoding: utf8);
}
