int _parseInt(String raw, int fallback) => int.tryParse(raw.trim()) ?? fallback;

double _parseDouble(String raw, double fallback) =>
    double.tryParse(raw.trim().replaceAll(',', '.')) ?? fallback;

int parseIntField(String raw, int fallback) => _parseInt(raw, fallback);

double parseDoubleField(String raw, double fallback) =>
    _parseDouble(raw, fallback);
