import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;

import '../json_util.dart';
import '../paths.dart';
import 'app_settings.dart';
import 'settings_clamp.dart';

class SettingsStore {
  SettingsStore({Directory? configDir})
      : _dir = configDir ?? ArgosPaths.configDir;

  final Directory _dir;

  File get file => File(p.join(_dir.path, 'settings.json'));

  Future<AppSettings> load() async {
    final settingsFile = file;
    if (!await settingsFile.exists()) {
      return const AppSettings();
    }
    try {
      final decoded = jsonDecode(await settingsFile.readAsString());
      return clampAppSettings(AppSettings.fromJson(asStringKeyedMap(decoded)));
    } catch (_) {
      return const AppSettings();
    }
  }

  Future<void> save(AppSettings settings) async {
    await _dir.create(recursive: true);
    await file.writeAsString(
      const JsonEncoder.withIndent('  ').convert(settings.toJson()),
    );
  }
}
