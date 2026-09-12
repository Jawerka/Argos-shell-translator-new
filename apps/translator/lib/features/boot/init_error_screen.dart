import 'dart:io';

import 'package:flutter/material.dart';
import 'package:translator_core/translator_core.dart';

import '../../l10n/app_localizations.dart';
import '../../providers.dart';

class InitErrorScreen extends StatelessWidget {
  const InitErrorScreen({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.appTitle)),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              l10n.bootFailedTitle,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            Expanded(child: SelectableText(message)),
            const SizedBox(height: 24),
            Semantics(
              button: true,
              label: l10n.openLog,
              child: FilledButton(
                onPressed: openLogFolder,
                child: Text(l10n.openLog),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

Future<void> openLogFolder() async {
  if (inFlutterTest()) {
    return;
  }
  try {
    final dir = ArgosPaths.logDir;
    await dir.create(recursive: true);
    if (Platform.isWindows) {
      await Process.start('explorer', [dir.path]);
    }
  } catch (_) {
    final repo = Directory.current;
    final fallback = Directory('${repo.path}${Platform.pathSeparator}log');
    if (Platform.isWindows && await fallback.exists()) {
      await Process.start('explorer', [fallback.path]);
    }
  }
}
