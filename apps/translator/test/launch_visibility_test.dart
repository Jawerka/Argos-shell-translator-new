import 'package:flutter_test/flutter_test.dart';
import 'package:translator/platform/launch_visibility.dart';

void main() {
  test('debug launch always shows the window', () {
    expect(
      shouldShowWindowAtLaunch(startMinimizedToTray: true, debugMode: true),
      isTrue,
    );
    expect(
      shouldShowWindowAtLaunch(startMinimizedToTray: false, debugMode: true),
      isTrue,
    );
  });

  test('release launch hides only when start_minimized_to_tray is set', () {
    expect(
      shouldShowWindowAtLaunch(startMinimizedToTray: true, debugMode: false),
      isFalse,
    );
    expect(
      shouldShowWindowAtLaunch(startMinimizedToTray: false, debugMode: false),
      isTrue,
    );
  });

  test('close-to-tray waits for tray init', () {
    expect(
      shouldHideWindowToTray(closeActionIsTray: true, trayInitialized: false),
      isFalse,
    );
    expect(
      shouldHideWindowToTray(closeActionIsTray: true, trayInitialized: true),
      isTrue,
    );
    expect(
      shouldHideWindowToTray(closeActionIsTray: false, trayInitialized: true),
      isFalse,
    );
  });

  test('start minimized hides only after tray is ready', () {
    expect(
      shouldHideAfterTrayInit(
        startMinimizedToTray: true,
        debugMode: false,
        trayInitialized: false,
      ),
      isFalse,
    );
    expect(
      shouldHideAfterTrayInit(
        startMinimizedToTray: true,
        debugMode: false,
        trayInitialized: true,
      ),
      isTrue,
    );
    expect(
      shouldHideAfterTrayInit(
        startMinimizedToTray: true,
        debugMode: true,
        trayInitialized: true,
      ),
      isFalse,
    );
  });
}
