import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:translator/core/theme/translator_theme.dart';
import 'package:translator/features/session/document_files.dart';
import 'package:translator/features/settings/settings_actions.dart';
import 'package:translator/features/shell/editor_style.dart';
import 'package:translator_core/translator_core.dart';

void main() {
  test('resolveOutputEncoding matches Python same/utf-8/utf-8-sig', () {
    expect(resolveOutputEncoding('cp1251', 'same'), 'cp1251');
    expect(resolveOutputEncoding('utf-8-sig', 'same'), 'utf-8');
    expect(resolveOutputEncoding('cp1251', 'utf-8'), 'utf-8');
    expect(resolveOutputEncoding('cp1251', 'utf-8-sig'), 'utf-8-sig');
    expect(resolveOutputEncoding(null, 'same'), 'utf-8');
  });

  test('writeEncodedTextFile writes utf-8-sig BOM', () async {
    final dir = await Directory.systemTemp.createTemp('argos_enc_');
    addTearDown(() => dir.delete(recursive: true));
    final path = '${dir.path}${Platform.pathSeparator}out.txt';
    await writeEncodedTextFile(
      path: path,
      content: 'Привет',
      encoding: 'utf-8-sig',
    );
    final bytes = await File(path).readAsBytes();
    expect(bytes.take(3).toList(), [0xEF, 0xBB, 0xBF]);
    expect(utf8.decode(bytes.sublist(3)), 'Привет');
  });

  test('writeEncodedTextFile writes utf-8 without BOM', () async {
    final dir = await Directory.systemTemp.createTemp('argos_enc_');
    addTearDown(() => dir.delete(recursive: true));
    final path = '${dir.path}${Platform.pathSeparator}out.txt';
    await writeEncodedTextFile(
      path: path,
      content: 'Hello',
      encoding: 'utf-8',
    );
    final bytes = await File(path).readAsBytes();
    expect(bytes.take(3).toList(), isNot([0xEF, 0xBB, 0xBF]));
    expect(utf8.decode(bytes), 'Hello');
  });

  test('exceedsLargeFileWarn is exclusive of the threshold', () {
    expect(exceedsLargeFileWarn(50000, 50000), isFalse);
    expect(exceedsLargeFileWarn(50001, 50000), isTrue);
  });

  test('shouldInstallBundleOnStart only after first-run without models', () {
    expect(
      shouldInstallBundleOnStart(
        bundleModelsOnStart: true,
        hasModels: false,
        firstRunDone: true,
        alreadyAttempted: false,
      ),
      isTrue,
    );
    expect(
      shouldInstallBundleOnStart(
        bundleModelsOnStart: true,
        hasModels: false,
        firstRunDone: false,
        alreadyAttempted: false,
      ),
      isFalse,
    );
    expect(
      shouldInstallBundleOnStart(
        bundleModelsOnStart: true,
        hasModels: true,
        firstRunDone: true,
        alreadyAttempted: false,
      ),
      isFalse,
    );
    expect(
      shouldInstallBundleOnStart(
        bundleModelsOnStart: true,
        hasModels: false,
        firstRunDone: true,
        alreadyAttempted: true,
      ),
      isFalse,
    );
  });

  test('editorTextStyle uses Consolas and scaled size', () {
    final style = editorTextStyle(
      const AppSettings(
        window: WindowSettings(editorFont: 'mono', fontScale: 1.5),
      ),
      TranslatorPalette.dark,
    );
    expect(style.fontFamily, 'Consolas');
    expect(style.fontSize, TranslatorPalette.fontSizeEditor * 1.5);
  });
}
