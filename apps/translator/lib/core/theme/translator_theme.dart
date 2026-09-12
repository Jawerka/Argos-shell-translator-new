import 'package:flutter/material.dart';

/// Токены из ui-mockups/css/tokens.css. Светлая тема — CTk COLOR_THEME_LIGHT.
class TranslatorPalette {
  const TranslatorPalette({
    required this.background,
    required this.backgroundElevated,
    required this.surface,
    required this.border,
    required this.textPrimary,
    required this.textMuted,
    required this.textEditor,
    required this.primary,
    required this.primaryHover,
    required this.primaryForeground,
    required this.accent,
    required this.accentHover,
    required this.accentForeground,
    required this.danger,
    required this.success,
    required this.warning,
    required this.focusRing,
    required this.input,
  });

  final Color background;
  final Color backgroundElevated;
  final Color surface;
  final Color border;
  final Color textPrimary;
  final Color textMuted;
  final Color textEditor;
  final Color primary;
  final Color primaryHover;
  final Color primaryForeground;
  final Color accent;
  final Color accentHover;
  final Color accentForeground;
  final Color danger;
  final Color success;
  final Color warning;
  final Color focusRing;
  final Color input;

  static const radiusControl = 3.0;
  static const radiusCard = 0.0;
  static const fontSizeUi = 13.0;
  static const fontSizeTitle = 16.0;
  static const fontSizeIntro = 15.0;
  static const fontSizeEditor = 14.0;

  static const dark = TranslatorPalette(
    background: Color(0xFF0F1115),
    backgroundElevated: Color(0xFF0B0C10),
    surface: Color(0xFF1B2230),
    border: Color(0xFF202A38),
    textPrimary: Color(0xFFE6EEF8),
    textMuted: Color(0xFF9AA3BF),
    textEditor: Color(0xFFB8C4D4),
    primary: Color(0xFF3890B5),
    primaryHover: Color(0xFF0F92E6),
    primaryForeground: Color(0xFF0B0C10),
    accent: Color(0xFF2F3542),
    accentHover: Color(0xFF3F4A63),
    accentForeground: Color(0xFFE6EEF8),
    danger: Color(0xFFFF7B95),
    success: Color(0xFF7BD389),
    warning: Color(0xFFF0C674),
    focusRing: Color(0xFF3890B5),
    input: Color(0xFF101216),
  );

  static const light = TranslatorPalette(
    background: Color(0xFFF0F2F5),
    backgroundElevated: Color(0xFFE4E6EB),
    surface: Color(0xFFFFFFFF),
    border: Color(0xFFD0D3D9),
    textPrimary: Color(0xFF1A1D21),
    textMuted: Color(0xFF5C6370),
    textEditor: Color(0xFF3D4554),
    primary: Color(0xFF0F92E6),
    primaryHover: Color(0xFF0878C7),
    primaryForeground: Color(0xFFFFFFFF),
    accent: Color(0xFFE4E6EB),
    accentHover: Color(0xFFD0D3D9),
    accentForeground: Color(0xFF1A1D21),
    danger: Color(0xFFC62828),
    success: Color(0xFF2E7D32),
    warning: Color(0xFFB8860B),
    focusRing: Color(0xFF0F92E6),
    input: Color(0xFFFFFFFF),
  );

  static TranslatorPalette forBrightness(Brightness brightness) =>
      brightness == Brightness.dark ? dark : light;
}

abstract final class TranslatorTheme {
  static ThemeData forPalette(TranslatorPalette palette) {
    final isDark = palette.background.computeLuminance() < 0.5;
    final scheme = (isDark ? ColorScheme.dark : ColorScheme.light)(
      surface: palette.background,
      primary: palette.primary,
      onPrimary: palette.primaryForeground,
      error: palette.danger,
      onSurface: palette.textPrimary,
      outline: palette.border,
    );

    OutlineInputBorder inputBorder([Color? color, double width = 1]) {
      return OutlineInputBorder(
        borderRadius: BorderRadius.circular(TranslatorPalette.radiusControl),
        borderSide: BorderSide(color: color ?? palette.border, width: width),
      );
    }

    const tap = MaterialTapTargetSize.shrinkWrap;
    const density = VisualDensity.compact;
    final controlShape = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(TranslatorPalette.radiusControl),
    );

    ButtonStyle compactStyle({
      required Color background,
      required Color foreground,
      required Color hover,
      Color? border,
      FontWeight weight = FontWeight.w400,
    }) {
      return ButtonStyle(
        backgroundColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.hovered) ||
              states.contains(WidgetState.pressed)) {
            return hover;
          }
          return background;
        }),
        foregroundColor: WidgetStatePropertyAll(foreground),
        overlayColor: const WidgetStatePropertyAll(Colors.transparent),
        elevation: const WidgetStatePropertyAll(0),
        shadowColor: const WidgetStatePropertyAll(Colors.transparent),
        tapTargetSize: tap,
        visualDensity: density,
        minimumSize: const WidgetStatePropertyAll(Size(0, MockupLayout.btnH)),
        maximumSize: const WidgetStatePropertyAll(
          Size(double.infinity, MockupLayout.btnH),
        ),
        padding: const WidgetStatePropertyAll(
          EdgeInsets.symmetric(horizontal: MockupLayout.space),
        ),
        shape: WidgetStatePropertyAll(controlShape),
        side: WidgetStatePropertyAll(
          BorderSide(color: border ?? Colors.transparent),
        ),
        textStyle: WidgetStatePropertyAll(
          TextStyle(
            fontFamily: 'Segoe UI',
            fontSize: TranslatorPalette.fontSizeUi,
            fontWeight: weight,
          ),
        ),
      );
    }

    return ThemeData(
      useMaterial3: true,
      brightness: isDark ? Brightness.dark : Brightness.light,
      colorScheme: scheme,
      scaffoldBackgroundColor: palette.background,
      dividerColor: palette.border,
      visualDensity: density,
      materialTapTargetSize: tap,
      focusColor: palette.focusRing.withValues(alpha: 0.28),
      hoverColor: palette.accentHover.withValues(alpha: 0.35),
      fontFamily: 'Segoe UI',
      fontFamilyFallback: const ['Segoe UI Variable', 'Segoe UI'],
      appBarTheme: AppBarTheme(
        backgroundColor: palette.backgroundElevated,
        foregroundColor: palette.textPrimary,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: palette.textPrimary,
          fontSize: TranslatorPalette.fontSizeTitle,
          fontWeight: FontWeight.w700,
          fontFamily: 'Segoe UI',
        ),
      ),
      cardTheme: CardThemeData(
        color: palette.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(TranslatorPalette.radiusCard),
          side: BorderSide(color: palette.border),
        ),
      ),
      dividerTheme: DividerThemeData(
        color: palette.border,
        thickness: 1,
        space: 1,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: palette.input,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: MockupLayout.space,
        ),
        border: inputBorder(),
        enabledBorder: inputBorder(),
        focusedBorder: inputBorder(palette.primary),
        disabledBorder: inputBorder(),
        hintStyle: TextStyle(
          color: palette.textMuted,
          fontSize: TranslatorPalette.fontSizeUi,
        ),
      ),
      textTheme: TextTheme(
        bodyMedium: TextStyle(
          color: palette.textPrimary,
          fontSize: TranslatorPalette.fontSizeUi,
          fontWeight: FontWeight.w400,
          height: 1.2,
        ),
        titleMedium: TextStyle(
          color: palette.textPrimary,
          fontWeight: FontWeight.w700,
          fontSize: TranslatorPalette.fontSizeTitle,
        ),
        labelSmall: TextStyle(
          color: palette.textMuted,
          fontSize: TranslatorPalette.fontSizeUi,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: compactStyle(
          background: palette.primary,
          foreground: palette.primaryForeground,
          hover: palette.primaryHover,
          weight: FontWeight.w700,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: compactStyle(
          background: palette.accent,
          foreground: palette.accentForeground,
          hover: palette.accentHover,
          border: palette.border,
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: compactStyle(
          background: Colors.transparent,
          foreground: palette.textPrimary,
          hover: palette.accent,
          border: palette.border,
        ),
      ),
      checkboxTheme: CheckboxThemeData(
        visualDensity: density,
        materialTapTargetSize: tap,
        side: BorderSide(color: palette.border),
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return palette.primary;
          }
          return Colors.transparent;
        }),
        checkColor: WidgetStatePropertyAll(palette.primaryForeground),
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: palette.primary,
        thumbColor: palette.primary,
        overlayShape: SliderComponentShape.noOverlay,
        trackHeight: 4,
      ),
      iconTheme: IconThemeData(color: palette.textMuted, size: 16),
    );
  }

  static ThemeData dark() => forPalette(TranslatorPalette.dark);

  static ThemeData light() => forPalette(TranslatorPalette.light);
}

/// Геометрия из ui-mockups/css (shared.css, main.css, settings.css).
abstract final class MockupLayout {
  static const space = 10.0;
  static const toolbarH = 50.0;
  static const panelHeaderH = 30.0;
  static const tabRowH = 30.0;
  static const tabRowMargin = 4.0;
  static const btnH = 30.0;
  static const btnPrimaryW = 100.0;
  static const btnAccentW = 100.0;
  static const btnAccentWideW = 170.0;
  static const btnIconW = 40.0;
  static const fieldH = 36.0;
  static const langComboH = 30.0;
  static const langComboMaxW = 180.0;
  static const settingsSidebarW = 170.0;
  static const settingsLabelW = 160.0;
  static const settingsMaxW = 720.0;
  static const settingsBodyMinH = 420.0;
  static const settingsHrBottom = 25.0;
  static const settingsSidebarPad = 6.0;
  static const settingsNavGap = 2.0;
  static const zoneGap = 6.0;
  static const headerControlsGap = 4.0;
  static const checkboxSize = 16.0;
  static const footerPadH = 4.0;
  static const footerPadV = 2.0;
  static const pickerMaxW = 440.0;
}
