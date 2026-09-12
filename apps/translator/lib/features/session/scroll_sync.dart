int paragraphIndexForRatio(List<int> starts, int totalChars, double ratio) {
  if (starts.isEmpty) {
    return 0;
  }
  final pos = (ratio.clamp(0.0, 1.0) * totalChars).floor();
  var idx = 0;
  for (var i = 0; i < starts.length; i++) {
    if (starts[i] <= pos) {
      idx = i;
    } else {
      break;
    }
  }
  return idx;
}

double ratioForParagraph(List<int> starts, int totalChars, int paraIdx) {
  if (starts.isEmpty || totalChars <= 0) {
    return 0;
  }
  if (paraIdx >= starts.length) {
    return 1;
  }
  if (paraIdx < 0) {
    return 0;
  }
  return (starts[paraIdx] / totalChars).clamp(0.0, 1.0);
}
