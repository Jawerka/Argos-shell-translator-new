Map<String, dynamic> asStringKeyedMap(Object? value) {
  if (value is Map<String, dynamic>) {
    return Map<String, dynamic>.from(value);
  }
  if (value is Map) {
    return value.map((key, dynamic v) => MapEntry(key.toString(), v));
  }
  return <String, dynamic>{};
}

int readInt(Object? value, int fallback) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return fallback;
}

double readDouble(Object? value, double fallback) {
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  return fallback;
}

String readString(Object? value, String fallback) {
  if (value is String) {
    return value;
  }
  return fallback;
}

bool readBool(Object? value, bool fallback) {
  if (value is bool) {
    return value;
  }
  return fallback;
}

Map<String, String> readStringMap(
  Object? value,
  Map<String, String> fallback,
) {
  if (value is Map) {
    return value.map(
      (key, dynamic v) => MapEntry(key.toString(), v?.toString() ?? ''),
    );
  }
  return Map<String, String>.from(fallback);
}
