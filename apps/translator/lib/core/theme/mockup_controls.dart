import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'translator_theme.dart';

export 'translator_theme.dart';

enum MockupButtonVariant { primary, accent, ghost }

class MockupCard extends StatelessWidget {
  const MockupCard({super.key, required this.child, this.padding});

  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final body = padding == null ? child : Padding(padding: padding!, child: child);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: palette.surface,
        border: Border.all(color: palette.border),
        borderRadius: BorderRadius.circular(TranslatorPalette.radiusCard),
      ),
      child: body,
    );
  }
}

/// Кнопка .btn / .btn-primary / .btn-accent / .btn-ghost / .btn-icon.
class MockupButton extends StatefulWidget {
  const MockupButton({
    super.key,
    required this.onPressed,
    this.label,
    this.icon,
    this.variant = MockupButtonVariant.accent,
    this.width,
    this.expand = false,
    this.alignStart = false,
    this.tooltip,
  }) : chromeOnly = false;

  /// Только внешний вид — для PopupMenuButton.child.
  const MockupButton.chrome({
    super.key,
    this.label,
    this.icon,
    this.variant = MockupButtonVariant.accent,
    this.width,
    this.expand = false,
    this.alignStart = false,
    this.tooltip,
  })  : onPressed = null,
        chromeOnly = true;

  final VoidCallback? onPressed;
  final String? label;
  final IconData? icon;
  final MockupButtonVariant variant;
  final double? width;
  final bool expand;
  final bool alignStart;
  final String? tooltip;
  final bool chromeOnly;

  @override
  State<MockupButton> createState() => _MockupButtonState();
}

class _MockupButtonState extends State<MockupButton> {
  var _hover = false;

  bool get _iconOnly =>
      widget.icon != null && (widget.label == null || widget.label!.isEmpty);

  double? get _resolvedWidth {
    if (widget.expand) {
      return null;
    }
    if (widget.width != null) {
      return widget.width;
    }
    if (_iconOnly) {
      return MockupLayout.btnIconW;
    }
    return switch (widget.variant) {
      MockupButtonVariant.primary => MockupLayout.btnPrimaryW,
      MockupButtonVariant.accent => MockupLayout.btnAccentW,
      MockupButtonVariant.ghost => null,
    };
  }

  @override
  Widget build(BuildContext context) {
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final colors = _colors(palette);
    final bg = _hover && widget.onPressed != null ? colors.$4 : colors.$1;
    final child = _face(palette, colors.$3);

    Widget box = SizedBox(
      width: widget.expand ? double.infinity : _resolvedWidth,
      height: MockupLayout.btnH,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(TranslatorPalette.radiusControl),
          border: Border.all(color: colors.$2),
        ),
        child: Padding(
          padding: EdgeInsets.symmetric(
            horizontal: _iconOnly ? 0 : MockupLayout.space,
          ),
          child: widget.alignStart
              ? Align(alignment: Alignment.centerLeft, child: child)
              : Center(child: child),
        ),
      ),
    );

    if (widget.chromeOnly) {
      if (widget.tooltip != null) {
        box = Tooltip(message: widget.tooltip!, child: box);
      }
      return box;
    }

    Widget button = MouseRegion(
      onEnter: (_) => setState(() => _hover = true),
      onExit: (_) => setState(() => _hover = false),
      child: GestureDetector(
        onTap: widget.onPressed,
        child: box,
      ),
    );
    if (widget.tooltip != null) {
      button = Tooltip(message: widget.tooltip!, child: button);
    }
    final semanticsLabel = widget.label ?? widget.tooltip;
    if (semanticsLabel != null) {
      button = Semantics(button: true, label: semanticsLabel, child: button);
    }
    return button;
  }

  Widget _face(TranslatorPalette palette, Color foreground) {
    final style = TextStyle(
      fontFamily: 'Segoe UI',
      fontSize: TranslatorPalette.fontSizeUi,
      fontWeight: widget.variant == MockupButtonVariant.primary
          ? FontWeight.w700
          : FontWeight.w400,
      color: foreground,
      height: 1.1,
    );
    if (_iconOnly) {
      return Icon(widget.icon, size: 16, color: foreground);
    }
    if (widget.icon != null) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(widget.icon, size: 16, color: foreground),
          const SizedBox(width: MockupLayout.zoneGap),
          Text(widget.label!, style: style),
        ],
      );
    }
    return Text(widget.label ?? '', style: style, overflow: TextOverflow.ellipsis);
  }

  (Color bg, Color border, Color fg, Color hover) _colors(
    TranslatorPalette palette,
  ) {
    return switch (widget.variant) {
      MockupButtonVariant.primary => (
          palette.primary,
          Colors.transparent,
          palette.primaryForeground,
          palette.primaryHover,
        ),
      MockupButtonVariant.accent => (
          palette.accent,
          Colors.transparent,
          palette.accentForeground,
          palette.accentHover,
        ),
      MockupButtonVariant.ghost => (
          Colors.transparent,
          palette.border,
          palette.textPrimary,
          palette.accent,
        ),
    };
  }
}

InputDecoration mockupFieldDecoration(
  TranslatorPalette palette, {
  String? hint,
  bool enabled = true,
}) {
  final border = OutlineInputBorder(
    borderRadius: BorderRadius.circular(TranslatorPalette.radiusControl),
    borderSide: BorderSide(color: palette.border),
  );
  return InputDecoration(
    hintText: hint,
    filled: true,
    fillColor: palette.input,
    isDense: true,
    enabled: enabled,
    contentPadding: const EdgeInsets.symmetric(horizontal: MockupLayout.space),
    border: border,
    enabledBorder: border,
    focusedBorder: border,
    disabledBorder: border,
  );
}

class MockupTextField extends StatelessWidget {
  const MockupTextField({
    super.key,
    this.controller,
    this.onChanged,
    this.hint,
    this.enabled = true,
    this.obscureText = false,
    this.keyboardType,
    this.inputFormatters,
    this.maxLines = 1,
    this.minLines,
    this.height,
  });

  final TextEditingController? controller;
  final ValueChanged<String>? onChanged;
  final String? hint;
  final bool enabled;
  final bool obscureText;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final int? maxLines;
  final int? minLines;
  final double? height;

  @override
  Widget build(BuildContext context) {
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final multiline = (maxLines ?? 1) != 1;
    final field = TextField(
      controller: controller,
      onChanged: onChanged,
      enabled: enabled,
      obscureText: obscureText,
      keyboardType: keyboardType,
      inputFormatters: inputFormatters,
      maxLines: multiline ? maxLines : 1,
      minLines: minLines,
      textAlignVertical: TextAlignVertical.center,
      style: TextStyle(
        fontFamily: 'Segoe UI',
        fontSize: TranslatorPalette.fontSizeUi,
        color: palette.textPrimary,
        height: 1.2,
      ),
      decoration: mockupFieldDecoration(palette, hint: hint, enabled: enabled),
    );
    if (multiline) {
      return field;
    }
    return SizedBox(height: height ?? MockupLayout.fieldH, child: field);
  }
}

class MockupSelect<T> extends StatelessWidget {
  const MockupSelect({
    super.key,
    required this.value,
    required this.items,
    required this.onChanged,
    this.height = MockupLayout.fieldH,
    this.semanticLabel,
  });

  final T value;
  final List<(T, String)> items;
  final ValueChanged<T> onChanged;
  final double height;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final values = items.map((item) => item.$1).toList();
    final resolved = values.contains(value) ? value : values.first;
    final dropdown = DropdownButtonHideUnderline(
      child: DropdownButton<T>(
        isExpanded: true,
        isDense: true,
        value: resolved,
        dropdownColor: palette.surface,
        iconEnabledColor: palette.textMuted,
        style: TextStyle(
          fontFamily: 'Segoe UI',
          fontSize: TranslatorPalette.fontSizeUi,
          color: palette.textPrimary,
        ),
        items: [
          for (final item in items)
            DropdownMenuItem<T>(
              value: item.$1,
              child: Text(item.$2, overflow: TextOverflow.ellipsis),
            ),
        ],
        onChanged: (next) {
          if (next != null) {
            onChanged(next);
          }
        },
      ),
    );
    Widget body = DecoratedBox(
      decoration: BoxDecoration(
        color: palette.input,
        borderRadius: BorderRadius.circular(TranslatorPalette.radiusControl),
        border: Border.all(color: palette.border),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: MockupLayout.space),
        child: dropdown,
      ),
    );
    body = SizedBox(height: height, child: body);
    if (semanticLabel != null) {
      body = Semantics(label: semanticLabel, child: body);
    }
    return body;
  }
}

class MockupCheckbox extends StatelessWidget {
  const MockupCheckbox({
    super.key,
    required this.value,
    required this.onChanged,
    this.label,
    this.compact = false,
    this.tooltip,
  });

  final bool value;
  final ValueChanged<bool> onChanged;
  final String? label;
  final bool compact;
  final String? tooltip;

  @override
  Widget build(BuildContext context) {
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final box = SizedBox(
      width: MockupLayout.checkboxSize,
      height: MockupLayout.checkboxSize,
      child: Checkbox(
        value: value,
        onChanged: (next) {
          if (next != null) {
            onChanged(next);
          }
        },
        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        visualDensity: VisualDensity.compact,
        side: BorderSide(color: palette.border),
      ),
    );
    Widget row;
    if (label == null || compact) {
      row = box;
    } else {
      row = Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          box,
          const SizedBox(width: MockupLayout.space),
          Expanded(
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => onChanged(!value),
              child: Text(
                label!,
                style: TextStyle(
                  fontSize: TranslatorPalette.fontSizeUi,
                  color: palette.textPrimary,
                ),
              ),
            ),
          ),
        ],
      );
    }
    if (tooltip != null) {
      row = Tooltip(message: tooltip!, child: row);
    }
    return Semantics(
      checked: value,
      label: label ?? tooltip,
      child: row,
    );
  }
}

class MockupTextInset extends StatelessWidget {
  const MockupTextInset({
    super.key,
    required this.controller,
    required this.style,
    this.scrollController,
    this.hint,
    this.readOnly = false,
  });

  final TextEditingController controller;
  final ScrollController? scrollController;
  final TextStyle style;
  final String? hint;
  final bool readOnly;

  @override
  Widget build(BuildContext context) {
    final palette = TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final radius = BorderRadius.circular(TranslatorPalette.radiusControl);
    // OutlineInputBorder (не InputBorder.none): Material hover/fill идут по r=3.
    final border = OutlineInputBorder(
      borderRadius: radius,
      borderSide: BorderSide.none,
    );
    return ClipRRect(
      borderRadius: radius,
      child: TextField(
        controller: controller,
        scrollController: scrollController,
        readOnly: readOnly,
        mouseCursor: readOnly ? SystemMouseCursors.basic : null,
        maxLines: null,
        expands: true,
        textAlignVertical: TextAlignVertical.top,
        style: style,
        cursorColor: palette.textEditor,
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: style.copyWith(color: palette.textMuted),
          filled: true,
          fillColor: palette.input,
          hoverColor: Colors.transparent,
          focusColor: Colors.transparent,
          border: border,
          enabledBorder: border,
          focusedBorder: border,
          disabledBorder: border,
          contentPadding: const EdgeInsets.all(MockupLayout.space),
        ),
      ),
    );
  }
}
