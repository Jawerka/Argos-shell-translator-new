/// Правила показа окна при старте (без window_manager — удобно тестировать).
bool shouldShowWindowAtLaunch({
  required bool startMinimizedToTray,
  required bool debugMode,
}) {
  if (debugMode) {
    return true;
  }
  return !startMinimizedToTray;
}

/// Крестик / hide-to-tray только если трей уже есть.
bool shouldHideWindowToTray({
  required bool closeActionIsTray,
  required bool trayInitialized,
}) {
  return closeActionIsTray && trayInitialized;
}

/// После initTray: прятать только start_minimized в release и только если трей жив.
bool shouldHideAfterTrayInit({
  required bool startMinimizedToTray,
  required bool debugMode,
  required bool trayInitialized,
}) {
  if (shouldShowWindowAtLaunch(
    startMinimizedToTray: startMinimizedToTray,
    debugMode: debugMode,
  )) {
    return false;
  }
  return trayInitialized;
}
