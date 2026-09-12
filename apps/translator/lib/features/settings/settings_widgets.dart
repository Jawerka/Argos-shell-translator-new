import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/theme/mockup_controls.dart';

class SettingsNavButton extends StatefulWidget {
  const SettingsNavButton({
    super.key,
    required this.label,
    required this.selected,
    required this.onPressed,
  });

  final String label;
  final bool selected;
  final VoidCallback onPressed;

  @override
  State<SettingsNavButton> createState() => _SettingsNavButtonState();
}

class _SettingsNavButtonState extends State<SettingsNavButton> {
  var _hover = false;

  @override
  Widget build(BuildContext context) {
    final palette =
        TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final Color background;
    if (widget.selected) {
      background = palette.primary;
    } else if (_hover) {
      background = palette.accent;
    } else {
      background = Colors.transparent;
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: MockupLayout.settingsNavGap),
      child: Semantics(
        button: true,
        selected: widget.selected,
        label: widget.label,
        child: MouseRegion(
          cursor: SystemMouseCursors.click,
          onEnter: (_) => setState(() => _hover = true),
          onExit: (_) => setState(() => _hover = false),
          child: GestureDetector(
            onTap: widget.onPressed,
            child: SizedBox(
              width: double.infinity,
              height: MockupLayout.btnH,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: background,
                  borderRadius:
                      BorderRadius.circular(TranslatorPalette.radiusControl),
                ),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: MockupLayout.space),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      widget.label,
                      style: TextStyle(
                        fontSize: TranslatorPalette.fontSizeUi,
                        fontWeight: FontWeight.w400,
                        color: widget.selected
                            ? palette.primaryForeground
                            : palette.textPrimary,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class SettingsIntro extends StatelessWidget {
  const SettingsIntro({super.key, required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final palette =
        TranslatorPalette.forBrightness(Theme.of(context).brightness);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          text,
          style: TextStyle(
            fontSize: TranslatorPalette.fontSizeIntro,
            color: palette.textMuted,
          ),
        ),
        const SizedBox(height: MockupLayout.space),
        Divider(height: 1, thickness: 1, color: palette.border),
        const SizedBox(height: MockupLayout.settingsHrBottom),
      ],
    );
  }
}

class SettingsFieldRow extends StatelessWidget {
  const SettingsFieldRow({
    super.key,
    required this.label,
    required this.child,
  });

  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final withColon = label.endsWith(':') ? label : '$label:';
    return Padding(
      padding: const EdgeInsets.only(bottom: MockupLayout.space),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          SizedBox(
            width: MockupLayout.settingsLabelW,
            child: Text(
              withColon,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: TranslatorPalette.fontSizeUi),
            ),
          ),
          const SizedBox(width: MockupLayout.space),
          Expanded(child: child),
        ],
      ),
    );
  }
}

class SettingsCheckbox extends StatelessWidget {
  const SettingsCheckbox({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: MockupLayout.space),
      child: MockupCheckbox(
        label: label,
        value: value,
        onChanged: onChanged,
      ),
    );
  }
}

class SettingsDropdown<T> extends StatelessWidget {
  const SettingsDropdown({
    super.key,
    required this.value,
    required this.items,
    required this.onChanged,
  });

  final T value;
  final List<(T, String)> items;
  final ValueChanged<T> onChanged;

  @override
  Widget build(BuildContext context) {
    return MockupSelect<T>(
      value: value,
      items: items,
      onChanged: onChanged,
      height: MockupLayout.fieldH,
    );
  }
}

class SettingsSliderRow extends StatelessWidget {
  const SettingsSliderRow({
    super.key,
    required this.label,
    required this.value,
    required this.min,
    required this.max,
    required this.display,
    required this.onChanged,
    this.sliderKey,
  });

  final String label;
  final double value;
  final double min;
  final double max;
  final String display;
  final ValueChanged<double> onChanged;
  final Key? sliderKey;

  @override
  Widget build(BuildContext context) {
    final palette =
        TranslatorPalette.forBrightness(Theme.of(context).brightness);
    return SettingsFieldRow(
      label: label,
      child: SizedBox(
        height: MockupLayout.fieldH,
        child: Row(
          children: [
            Expanded(
              child: Slider(
                key: sliderKey,
                value: value.clamp(min, max),
                min: min,
                max: max,
                onChanged: onChanged,
              ),
            ),
            SizedBox(
              width: 48,
              child: Text(
                display,
                textAlign: TextAlign.right,
                style: TextStyle(
                  fontSize: TranslatorPalette.fontSizeUi,
                  color: palette.textMuted,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class SettingsMuted extends StatelessWidget {
  const SettingsMuted({super.key, required this.text, this.warning = false});

  final String text;
  final bool warning;

  @override
  Widget build(BuildContext context) {
    final palette =
        TranslatorPalette.forBrightness(Theme.of(context).brightness);
    return Padding(
      padding: const EdgeInsets.only(bottom: MockupLayout.space),
      child: Text(
        text,
        style: TextStyle(
          fontSize: TranslatorPalette.fontSizeUi,
          color: warning ? palette.warning : palette.textMuted,
        ),
      ),
    );
  }
}

class SettingsIntField extends StatelessWidget {
  const SettingsIntField({
    super.key,
    required this.controller,
    this.onChanged,
  });

  final TextEditingController controller;
  final ValueChanged<String>? onChanged;

  @override
  Widget build(BuildContext context) {
    return MockupTextField(
      controller: controller,
      keyboardType: TextInputType.number,
      inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'-?\d*'))],
      onChanged: onChanged,
    );
  }
}

class SettingsActionColumn extends StatelessWidget {
  const SettingsActionColumn({super.key, required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = 0; i < children.length; i++) ...[
          if (i > 0) const SizedBox(height: MockupLayout.space),
          children[i],
        ],
      ],
    );
  }
}

class SettingsBanner extends StatelessWidget {
  const SettingsBanner({
    super.key,
    required this.message,
    required this.isError,
    required this.retryLabel,
    required this.closeLabel,
    this.onRetry,
    required this.onClose,
  });

  final String message;
  final bool isError;
  final String retryLabel;
  final String closeLabel;
  final VoidCallback? onRetry;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    final palette =
        TranslatorPalette.forBrightness(Theme.of(context).brightness);
    return Padding(
      padding: const EdgeInsets.only(bottom: MockupLayout.space),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: isError
              ? palette.danger.withValues(alpha: 0.12)
              : palette.backgroundElevated,
          border: Border.all(color: palette.border),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: MockupLayout.space,
            vertical: MockupLayout.space,
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  message,
                  style: TextStyle(
                    fontSize: TranslatorPalette.fontSizeUi,
                    color: isError ? palette.danger : palette.textPrimary,
                  ),
                ),
              ),
              if (onRetry != null)
                MockupButton(
                  variant: MockupButtonVariant.ghost,
                  label: retryLabel,
                  onPressed: onRetry,
                ),
              MockupButton(
                variant: MockupButtonVariant.ghost,
                icon: Icons.close,
                tooltip: closeLabel,
                onPressed: onClose,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
