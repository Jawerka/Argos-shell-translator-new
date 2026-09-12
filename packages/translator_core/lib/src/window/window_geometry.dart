/// Геометрия окна без зависимости от Flutter.
class WindowGeometry {
  const WindowGeometry({
    required this.left,
    required this.top,
    required this.width,
    required this.height,
    this.maximized = false,
  });

  final double left;
  final double top;
  final double width;
  final double height;
  final bool maximized;

  static const minWidth = 800.0;
  static const minHeight = 600.0;
  static const defaultWidth = 1000.0;
  static const defaultHeight = 700.0;

  static const WindowGeometry defaults = WindowGeometry(
    left: 100,
    top: 100,
    width: defaultWidth,
    height: defaultHeight,
  );

  /// Оставить на экране хотя бы ~80×80 px; минимум 800×600 (PRODUCT).
  WindowGeometry clampToVisible() {
    var w = width < minWidth ? minWidth : width;
    var h = height < minHeight ? minHeight : height;
    var nextLeft = left;
    var nextTop = top;
    if (nextLeft < -w + 80) {
      nextLeft = 40;
    }
    if (nextTop < -40) {
      nextTop = 40;
    }
    if (nextLeft > 4000) {
      nextLeft = 40;
    }
    if (nextTop > 3000) {
      nextTop = 40;
    }
    return WindowGeometry(
      left: nextLeft,
      top: nextTop,
      width: w,
      height: h,
      maximized: maximized,
    );
  }

  Map<String, Object?> toJson() => {
        'left': left,
        'top': top,
        'width': width,
        'height': height,
        'maximized': maximized,
      };

  factory WindowGeometry.fromJson(Map<String, dynamic> json) {
    final left = (json['left'] as num?)?.toDouble();
    final top = (json['top'] as num?)?.toDouble();
    final width = (json['width'] as num?)?.toDouble();
    final height = (json['height'] as num?)?.toDouble();
    if (left == null || top == null || width == null || height == null) {
      return defaults;
    }
    return WindowGeometry(
      left: left,
      top: top,
      width: width,
      height: height,
      maximized: json['maximized'] == true,
    );
  }
}
