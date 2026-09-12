import 'package:flutter/material.dart';

import '../../core/theme/mockup_controls.dart';
import '../../l10n/app_localizations.dart';

Future<String?> showModelPickerDialog({
  required BuildContext context,
  required List<String> models,
  String? selected,
}) {
  return showDialog<String>(
    context: context,
    barrierColor: const Color(0x73000000),
    builder: (context) => _ModelPickerDialog(
      models: models,
      selected: selected,
    ),
  );
}

class _ModelPickerDialog extends StatefulWidget {
  const _ModelPickerDialog({required this.models, this.selected});

  final List<String> models;
  final String? selected;

  @override
  State<_ModelPickerDialog> createState() => _ModelPickerDialogState();
}

class _ModelPickerDialogState extends State<_ModelPickerDialog> {
  late final TextEditingController _search;
  String? _selected;

  @override
  void initState() {
    super.initState();
    _search = TextEditingController();
    final initial = widget.selected?.trim() ?? '';
    if (initial.isNotEmpty && widget.models.contains(initial)) {
      _selected = initial;
    } else if (widget.models.isNotEmpty) {
      _selected = widget.models.first;
    }
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  List<String> get _filtered {
    final query = _search.text.trim().toLowerCase();
    if (query.isEmpty) {
      return widget.models;
    }
    return widget.models
        .where((name) => name.toLowerCase().contains(query))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette =
        TranslatorPalette.forBrightness(Theme.of(context).brightness);
    final items = _filtered;
    final selected = items.contains(_selected)
        ? _selected
        : (items.isEmpty ? null : items.first);

    return Dialog(
      backgroundColor: palette.background,
      insetPadding: const EdgeInsets.all(MockupLayout.space),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(TranslatorPalette.radiusCard),
        side: BorderSide(color: palette.border),
      ),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: MockupLayout.pickerMaxW),
        child: Padding(
          padding: const EdgeInsets.all(MockupLayout.space),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.only(bottom: MockupLayout.space),
                child: Text(
                  l10n.settingsPickerTitle,
                  style: const TextStyle(
                    fontSize: TranslatorPalette.fontSizeTitle,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              MockupTextField(
                key: const Key('model-picker-search'),
                controller: _search,
                hint: l10n.settingsPickerSearch,
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: MockupLayout.space),
              if (items.isEmpty)
                SizedBox(
                  height: MockupLayout.fieldH,
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      l10n.settingsLlmModelsEmpty,
                      style: TextStyle(
                        fontSize: TranslatorPalette.fontSizeUi,
                        color: palette.textMuted,
                      ),
                    ),
                  ),
                )
              else
                MockupSelect<String>(
                  value: selected ?? items.first,
                  items: [for (final name in items) (name, name)],
                  onChanged: (name) => setState(() => _selected = name),
                ),
              const SizedBox(height: MockupLayout.space),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  MockupButton(
                    variant: MockupButtonVariant.primary,
                    label: l10n.settingsPickerSelect,
                    onPressed: selected == null
                        ? null
                        : () => Navigator.pop(context, selected),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
