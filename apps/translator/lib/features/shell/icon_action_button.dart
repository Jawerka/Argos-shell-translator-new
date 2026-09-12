import 'package:flutter/material.dart';

import '../../core/theme/mockup_controls.dart';

class IconActionButton extends StatelessWidget {
  const IconActionButton({
    super.key,
    required this.icon,
    required this.tooltip,
    required this.onPressed,
    this.filled = true,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback? onPressed;
  final bool filled;

  @override
  Widget build(BuildContext context) {
    return MockupButton(
      icon: icon,
      tooltip: tooltip,
      onPressed: onPressed,
      variant: filled ? MockupButtonVariant.accent : MockupButtonVariant.ghost,
      width: MockupLayout.btnIconW,
    );
  }
}
