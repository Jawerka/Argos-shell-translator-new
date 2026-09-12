/// Правила swap: AUTO остаётся AUTO; цель меняется по фактической паре.
({String from, String to}) swapLanguagePair({
  required String langFrom,
  required String langTo,
  String? detectedLang,
  String? resolvedTo,
}) {
  if (langFrom == 'auto') {
    final actualTo = (resolvedTo ?? langTo).trim();
    final detected = detectedLang?.trim();
    if (detected != null && detected.isNotEmpty && detected != actualTo) {
      return (from: 'auto', to: detected);
    }
    final nextTo = actualTo == 'ru' ? 'en' : 'ru';
    return (from: 'auto', to: nextTo);
  }

  final newFrom = langTo;
  var newTo = langFrom;
  if (newTo == 'auto') {
    newTo = langFrom;
  }
  return (from: newFrom, to: newTo);
}
