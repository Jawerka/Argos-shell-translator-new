import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hotkey_manager/hotkey_manager.dart';
import 'package:translator/platform/hotkey_parse.dart';

void main() {
  test('empty hotkey is null', () {
    expect(parseGlobalHotkey(''), isNull);
    expect(parseGlobalHotkey('   '), isNull);
  });

  test('plain Copy ctrl+c is blocked', () {
    expect(parseGlobalHotkey('ctrl+c'), isNull);
    expect(parseGlobalHotkey('control+c'), isNull);
  });

  test('ctrl+shift+c parses', () {
    final hotkey = parseGlobalHotkey('ctrl+shift+c');
    expect(hotkey, isNotNull);
    expect(hotkey!.key, LogicalKeyboardKey.keyC);
    expect(hotkey.modifiers, containsAll([HotKeyModifier.control, HotKeyModifier.shift]));
    expect(hotkey.scope, HotKeyScope.system);
  });

  test('alt+f9 parses', () {
    final hotkey = parseGlobalHotkey('alt+f9');
    expect(hotkey, isNotNull);
    expect(hotkey!.key, LogicalKeyboardKey.f9);
    expect(hotkey.modifiers, [HotKeyModifier.alt]);
  });

  test('unknown token is null', () {
    expect(parseGlobalHotkey('ctrl+foo'), isNull);
    expect(parseGlobalHotkey('hyper+c'), isNull);
  });
}
