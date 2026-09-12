import 'dart:io';

import '../../core/app_log.dart';
import '../../providers.dart';

const argosModelsCatalogUrl = 'https://www.argosopentech.com/argospm/';

/// Комплект моделей при старте — один раз, после first-run, если пар нет.
bool shouldInstallBundleOnStart({
  required bool bundleModelsOnStart,
  required bool hasModels,
  required bool firstRunDone,
  required bool alreadyAttempted,
}) {
  return bundleModelsOnStart && firstRunDone && !hasModels && !alreadyAttempted;
}

Future<void> openDirectoryInExplorer(String path) async {
  if (inFlutterTest() || path.trim().isEmpty) {
    return;
  }
  try {
    final dir = Directory(path);
    await dir.create(recursive: true);
    if (Platform.isWindows) {
      await Process.start('explorer', [dir.path]);
    }
  } catch (e, st) {
    AppLog.warning('open packages dir failed', e, st);
  }
}

Future<void> openExternalUrl(String url) async {
  if (inFlutterTest()) {
    return;
  }
  try {
    if (Platform.isWindows) {
      await Process.start('cmd', ['/c', 'start', '', url]);
    }
  } catch (e, st) {
    AppLog.warning('open url failed', e, st);
  }
}
