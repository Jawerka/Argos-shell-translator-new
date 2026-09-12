import 'package:path/path.dart' as p;

/// Расширения текстовых файлов для DnD / диалога открытия.
const supportedTextExtensions = <String>{
  '.txt',
  '.md',
  '.markdown',
  '.csv',
  '.json',
  '.xml',
  '.html',
  '.htm',
  '.yaml',
  '.yml',
  '.ini',
  '.cfg',
  '.log',
  '.rst',
  '.toml',
};

bool isSupportedTextPath(String path) =>
    supportedTextExtensions.contains(p.extension(path).toLowerCase());

/// Имя выходного файла, как Python `suggest_output_path`.
String suggestOutputPath(
  String src, {
  String suffix = '_translated',
  String engine = 'argos',
}) {
  final cleanSuffix = suffix.isEmpty ? '_translated' : suffix;
  final dir = p.dirname(src);
  final ext = p.extension(src);
  final stem = p.basenameWithoutExtension(src);
  final name =
      engine == 'llm' ? '$stem${cleanSuffix}_llm$ext' : '$stem$cleanSuffix$ext';
  if (dir == '.' || dir.isEmpty) {
    return name;
  }
  return p.join(dir, name);
}
