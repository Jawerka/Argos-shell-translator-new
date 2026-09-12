import 'dart:io';

import 'package:path/path.dart' as p;

/// Каталоги профиля `%USERPROFILE%\.argos_translate`.
abstract final class ArgosPaths {
  static String get userHome {
    final env = Platform.environment;
    return env['USERPROFILE'] ?? env['HOME'] ?? Directory.systemTemp.path;
  }

  static Directory get configDir =>
      Directory(p.join(userHome, '.argos_translate'));

  static File get settingsFile => File(p.join(configDir.path, 'settings.json'));

  static File get windowStateFile =>
      File(p.join(configDir.path, 'window_state.json'));

  static Directory get logDir => Directory(p.join(configDir.path, 'log'));

  static File get appLogFile => File(p.join(logDir.path, 'app.log'));
}
