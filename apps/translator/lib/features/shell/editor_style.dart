import 'package:flutter/material.dart';
import 'package:translator_core/translator_core.dart';

import '../../core/theme/translator_theme.dart';

TextStyle editorTextStyle(AppSettings settings, TranslatorPalette palette) {
  final mono = settings.window.editorFont == 'mono';
  final scale = settings.window.fontScale <= 0 ? 1.0 : settings.window.fontScale;
  return TextStyle(
    fontFamily: mono ? 'Consolas' : 'Segoe UI Variable',
    fontFamilyFallback: mono
        ? const <String>['Courier New', 'Courier']
        : const <String>['Segoe UI', 'sans-serif'],
    fontSize: TranslatorPalette.fontSizeEditor * scale,
    color: palette.textEditor,
    height: 1.45,
  );
}
