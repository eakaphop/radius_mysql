import { useTranslation } from "react-i18next";

import { Button, Input, Select } from "@/components/ui/primitives";
import { RADIUS_OPERATORS } from "@/lib/radius";

export interface AttributeRow {
  attribute: string;
  op: string;
  value: string;
}

interface AttributeEditorProps {
  label: string;
  rows: AttributeRow[];
  onChange: (rows: AttributeRow[]) => void;
}

/** key-op-value editor for radcheck/radreply style attribute lists. */
export function AttributeEditor({ label, rows, onChange }: AttributeEditorProps) {
  const { t } = useTranslation();

  const updateRow = (index: number, patch: Partial<AttributeRow>) => {
    onChange(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  };

  return (
    <div className="space-y-2">
      <span className="text-sm font-medium">{label}</span>
      {rows.map((row, index) => (
        <div key={index} className="flex items-center gap-2">
          <Input
            aria-label={t("attributes.attribute")}
            placeholder={t("attributes.attribute")}
            value={row.attribute}
            onChange={(event) => updateRow(index, { attribute: event.target.value })}
          />
          <Select
            aria-label={t("attributes.operator")}
            value={row.op}
            onChange={(event) => updateRow(index, { op: event.target.value })}
          >
            {RADIUS_OPERATORS.map((op) => (
              <option key={op} value={op}>
                {op}
              </option>
            ))}
          </Select>
          <Input
            aria-label={t("attributes.value")}
            placeholder={t("attributes.value")}
            value={row.value}
            onChange={(event) => updateRow(index, { value: event.target.value })}
          />
          <Button
            type="button"
            variant="danger"
            onClick={() => onChange(rows.filter((_, i) => i !== index))}
          >
            {t("common.remove")}
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="secondary"
        onClick={() => onChange([...rows, { attribute: "", op: ":=", value: "" }])}
      >
        {t("attributes.addRow")}
      </Button>
    </div>
  );
}
