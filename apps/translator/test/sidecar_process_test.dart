import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:translator/platform/sidecar_process.dart';

void main() {
  test('sidecarLaunchCandidates lists exeDir then sidecar subfolder', () {
    final exeDir = Directory(p.join('fake', 'ArgosTranslate'));
    expect(
      sidecarLaunchCandidates(exeDir),
      [
        p.join(exeDir.path, 'argos_sidecar.exe'),
        p.join(exeDir.path, 'sidecar', 'argos_sidecar.exe'),
      ],
    );
  });

  test('resolveFrozenSidecar prefers sidecar/argos_sidecar.exe when nested', () {
    final exeDir = Directory.systemTemp.createTempSync('argos-stage-');
    addTearDown(() {
      if (exeDir.existsSync()) {
        exeDir.deleteSync(recursive: true);
      }
    });
    final nested = File(p.join(exeDir.path, 'sidecar', 'argos_sidecar.exe'));
    nested.parent.createSync(recursive: true);
    nested.writeAsBytesSync(const [0]);

    final resolved = resolveFrozenSidecar(exeDir);
    expect(resolved, isNotNull);
    expect(p.normalize(resolved!.path), p.normalize(nested.path));
  });

  test('resolveFrozenSidecar prefers exeDir sidecar when both exist', () {
    final exeDir = Directory.systemTemp.createTempSync('argos-stage-');
    addTearDown(() {
      if (exeDir.existsSync()) {
        exeDir.deleteSync(recursive: true);
      }
    });
    final rootExe = File(p.join(exeDir.path, 'argos_sidecar.exe'));
    rootExe.writeAsBytesSync(const [0]);
    final nested = File(p.join(exeDir.path, 'sidecar', 'argos_sidecar.exe'));
    nested.parent.createSync(recursive: true);
    nested.writeAsBytesSync(const [1]);

    final resolved = resolveFrozenSidecar(exeDir);
    expect(p.normalize(resolved!.path), p.normalize(rootExe.path));
  });

  test('parseSidecarReadyJson accepts ready line', () {
    final parsed = parseSidecarReadyJson('{"ok": true, "port": 54321}\n');
    expect(parsed, isNotNull);
    expect(parsed!['ok'], isTrue);
    expect((parsed['port'] as num).toInt(), 54321);
  });

  test('parseSidecarReadyJson rejects junk', () {
    expect(parseSidecarReadyJson('not json'), isNull);
    expect(parseSidecarReadyJson('{"ok": false, "port": 1}'), isNull);
    expect(parseSidecarReadyJson(''), isNull);
  });

  test('buildSidecarLaunchArgs includes packages-dir when set', () {
    expect(
      buildSidecarLaunchArgs(token: 'tok'),
      ['--host', '127.0.0.1', '--port', '0', '--token', 'tok'],
    );
    expect(
      buildSidecarLaunchArgs(token: 'tok', packagesDir: r'C:\models'),
      [
        '--host',
        '127.0.0.1',
        '--port',
        '0',
        '--token',
        'tok',
        '--packages-dir',
        r'C:\models',
      ],
    );
    expect(
      buildSidecarLaunchArgs(token: 'tok', packagesDir: '  '),
      ['--host', '127.0.0.1', '--port', '0', '--token', 'tok'],
    );
  });
}
