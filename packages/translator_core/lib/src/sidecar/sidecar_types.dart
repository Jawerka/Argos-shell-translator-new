import '../json_util.dart';

class TranslateRequest {
  const TranslateRequest({
    required this.text,
    this.fromCode = 'auto',
    this.toCode = 'ru',
    this.preferApi = true,
    this.translateCodeBlocks = false,
    this.cache = false,
    this.cacheSize = 500,
    this.packagesDir,
  });

  final String text;
  final String fromCode;
  final String toCode;
  final bool preferApi;
  final bool translateCodeBlocks;
  final bool cache;
  final int cacheSize;
  final String? packagesDir;

  Map<String, Object?> toJson() {
    final json = <String, Object?>{
      'text': text,
      'from': fromCode,
      'to': toCode,
      'prefer_api': preferApi,
      'translate_code_blocks': translateCodeBlocks,
      'cache': cache,
      'cache_size': cacheSize,
    };
    if (packagesDir != null) {
      json['packages_dir'] = packagesDir;
    }
    return json;
  }
}

sealed class TranslateEvent {
  const TranslateEvent();

  factory TranslateEvent.fromJson(Map<String, dynamic> json) {
    switch (json['type']?.toString()) {
      case 'start':
        return TranslateStart.fromJson(json);
      case 'chunk':
        return TranslateChunk.fromJson(json);
      case 'done':
        return TranslateDone.fromJson(json);
      case 'error':
        return TranslateError.fromJson(json);
      case 'cancelled':
        return TranslateCancelled.fromJson(json);
      default:
        throw FormatException(
          'unknown translate event: ${json['type']}',
        );
    }
  }
}

final class TranslateStart extends TranslateEvent {
  const TranslateStart({
    required this.jobId,
    required this.fromCode,
    required this.toCode,
    required this.unitCount,
  });

  final int jobId;
  final String fromCode;
  final String toCode;
  final int unitCount;

  factory TranslateStart.fromJson(Map<String, dynamic> json) {
    return TranslateStart(
      jobId: readInt(json['job_id'], 0),
      fromCode: readString(json['from'], ''),
      toCode: readString(json['to'], ''),
      unitCount: readInt(json['unit_count'], 0),
    );
  }
}

final class TranslateChunk extends TranslateEvent {
  const TranslateChunk({
    required this.jobId,
    required this.index,
    required this.paraIdx,
    required this.text,
    required this.done,
    required this.total,
  });

  final int jobId;
  final int index;
  final int paraIdx;
  final String text;
  final int done;
  final int total;

  factory TranslateChunk.fromJson(Map<String, dynamic> json) {
    return TranslateChunk(
      jobId: readInt(json['job_id'], 0),
      index: readInt(json['index'], 0),
      paraIdx: readInt(json['para_idx'], 0),
      text: readString(json['text'], ''),
      done: readInt(json['done'], 0),
      total: readInt(json['total'], 0),
    );
  }
}

final class TranslateDone extends TranslateEvent {
  const TranslateDone({required this.jobId});

  final int jobId;

  factory TranslateDone.fromJson(Map<String, dynamic> json) {
    return TranslateDone(jobId: readInt(json['job_id'], 0));
  }
}

final class TranslateError extends TranslateEvent {
  const TranslateError({this.jobId, required this.message});

  final int? jobId;
  final String message;

  factory TranslateError.fromJson(Map<String, dynamic> json) {
    return TranslateError(
      jobId: _readOptionalInt(json['job_id']),
      message: readString(json['message'], ''),
    );
  }
}

final class TranslateCancelled extends TranslateEvent {
  const TranslateCancelled({this.jobId});

  final int? jobId;

  factory TranslateCancelled.fromJson(Map<String, dynamic> json) {
    return TranslateCancelled(jobId: _readOptionalInt(json['job_id']));
  }
}

class DetectResult {
  const DetectResult({
    required this.code,
    required this.label,
    this.lang = '',
  });

  final String code;
  final String label;

  /// `ru` или метка языка без подгонки под модели Argos.
  final String lang;

  factory DetectResult.fromJson(Map<String, dynamic> json) {
    final code = readString(json['code'], '');
    return DetectResult(
      code: code,
      label: readString(json['label'], ''),
      lang: readString(json['lang'], code),
    );
  }
}

class SidecarLanguages {
  const SidecarLanguages({required this.languages});

  final Map<String, String> languages;

  factory SidecarLanguages.fromJson(Map<String, dynamic> json) {
    return SidecarLanguages(
      languages: readStringMap(json['languages'], const {}),
    );
  }
}

class SidecarModels {
  const SidecarModels({
    this.pairs = const [],
    this.packagesDir,
  });

  final List<Object?> pairs;
  final String? packagesDir;

  factory SidecarModels.fromJson(Map<String, dynamic> json) {
    final rawPairs = json['pairs'];
    return SidecarModels(
      pairs: rawPairs is List ? List<Object?>.from(rawPairs) : const [],
      packagesDir: json['packages_dir'] is String
          ? json['packages_dir'] as String
          : null,
    );
  }
}

class DecodedDocument {
  const DecodedDocument({
    required this.text,
    required this.encoding,
    required this.confidence,
    required this.fileType,
    required this.path,
  });

  final String text;
  final String encoding;
  final double confidence;
  final String fileType;
  final String path;

  factory DecodedDocument.fromJson(Map<String, dynamic> json) {
    return DecodedDocument(
      text: readString(json['text'], ''),
      encoding: readString(json['encoding'], ''),
      confidence: readDouble(json['confidence'], 0),
      fileType: readString(json['file_type'], ''),
      path: readString(json['path'], ''),
    );
  }
}

class InstallModelsResult {
  const InstallModelsResult({
    required this.installed,
    this.pairs = const [],
  });

  final int installed;
  final List<Object?> pairs;

  factory InstallModelsResult.fromJson(Map<String, dynamic> json) {
    final rawPairs = json['pairs'];
    return InstallModelsResult(
      installed: readInt(json['installed'], 0),
      pairs: rawPairs is List ? List<Object?>.from(rawPairs) : const [],
    );
  }
}

int? _readOptionalInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return null;
}
