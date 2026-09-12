/// Правила swap: AUTO остаётся AUTO; цель меняется по chip или ru↔en.
({String from, String to}) swapLanguagePair({
  required String langFrom,
  required String langTo,
  String? detectedLang,
}) {
  if (langFrom == 'auto') {
    final detected = detectedLang?.trim();
    if (detected != null && detected.isNotEmpty && detected != langTo) {
      return (from: 'auto', to: detected);
    }
    final nextTo = langTo == 'ru' ? 'en' : 'ru';
    return (from: 'auto', to: nextTo);
  }

  final newFrom = langTo;
  var newTo = langFrom;
  if (newTo == 'auto') {
    newTo = langFrom;
  }
  return (from: newFrom, to: newTo);
}
