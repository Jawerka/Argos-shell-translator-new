/// Явная пара: стороны меняются местами. AUTO-свап живёт в контроллере сессии.
({String from, String to}) swapLanguagePair({
  required String langFrom,
  required String langTo,
}) {
  final newFrom = langTo;
  var newTo = langFrom;
  if (newTo == 'auto') {
    newTo = 'ru';
  }
  return (from: newFrom, to: newTo);
}

/// Вставка целиком, а не правка: общий префикс и суффикс короче половины.
bool sourceTextReplaced(String previous, String next) {
  if (previous == next) {
    return false;
  }
  if (previous.isEmpty || next.isEmpty) {
    return true;
  }
  var prefix = 0;
  final maxPrefix = previous.length < next.length ? previous.length : next.length;
  while (prefix < maxPrefix &&
      previous.codeUnitAt(prefix) == next.codeUnitAt(prefix)) {
    prefix += 1;
  }
  var suffix = 0;
  final prevRemain = previous.length - prefix;
  final nextRemain = next.length - prefix;
  final maxSuffix = prevRemain < nextRemain ? prevRemain : nextRemain;
  while (suffix < maxSuffix &&
      previous.codeUnitAt(previous.length - 1 - suffix) ==
          next.codeUnitAt(next.length - 1 - suffix)) {
    suffix += 1;
  }
  final shared = prefix + suffix;
  final longer = previous.length > next.length ? previous.length : next.length;
  return shared * 2 < longer;
}
