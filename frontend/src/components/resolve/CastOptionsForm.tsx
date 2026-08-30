import {
  applyCastOptionChange,
  getCastOptionFieldState,
} from "../../lib/castOptionConstraints";
import {
  castOptionEnumValues,
  castOptionFieldLabel,
  castOptionFieldType,
  castOptionPlaceholder,
  formatCastOptionDefault,
  type JsonSchemaProperty,
} from "../../lib/castOptionsSchema";
import { cn } from "../ui/cn";

const compactInputClass =
  "w-full rounded border border-slate-300 bg-surface-elevated px-1.5 py-0.5 text-[11px] dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200";

interface CastOptionsFormProps {
  schema: Record<string, unknown>;
  values: Record<string, string | boolean>;
  onChange: (values: Record<string, string | boolean>) => void;
  className?: string;
}

function FieldHint({ prop }: { prop: JsonSchemaProperty }) {
  const defaultLabel = formatCastOptionDefault(prop);
  if (!defaultLabel) return null;
  return (
    <p className="mt-0.5 text-[9px] leading-snug text-gray-400">
      Default: <span className="font-mono">{defaultLabel}</span>
    </p>
  );
}

export function CastOptionsForm({
  schema,
  values,
  onChange,
  className,
}: CastOptionsFormProps) {
  const properties = (schema.properties ?? {}) as Record<
    string,
    JsonSchemaProperty
  >;
  const keys = Object.keys(properties);
  if (keys.length === 0) {
    return (
      <p className="text-[10px] text-gray-400">No options for this format.</p>
    );
  }

  const setValue = (key: string, value: string | boolean) => {
    onChange(applyCastOptionChange(key, value, properties, values));
  };

  const schemaDescription =
    typeof schema.description === "string" ? schema.description : undefined;

  return (
    <div className={cn("space-y-2", className)}>
      {schemaDescription && (
        <p className="text-[10px] leading-snug text-gray-400">
          {schemaDescription}
        </p>
      )}
      {keys.map((key) => {
        const prop = properties[key]!;
        const fieldState = getCastOptionFieldState(
          key,
          prop,
          properties,
          values,
        );
        const options = castOptionEnumValues(prop);
        const type = castOptionFieldType(prop);
        const label = castOptionFieldLabel(key, prop);
        const description = prop.description;
        const placeholder = castOptionPlaceholder(prop);
        const disabledClass = fieldState.disabled ? "opacity-50" : "";

        if (type === "boolean") {
          const defaultChecked = prop.default === true;
          const checked = fieldState.disabled
            ? false
            : key in values
              ? Boolean(values[key])
              : defaultChecked;
          return (
            <label
              key={key}
              className={cn(
                "flex items-start gap-1.5 text-[11px] text-gray-600 dark:text-gray-300",
                disabledClass,
              )}
            >
              <input
                type="checkbox"
                checked={checked}
                disabled={fieldState.disabled}
                onChange={(e) => setValue(key, e.target.checked)}
                className="mt-0.5 rounded"
              />
              <span className="min-w-0">
                <span>{label}</span>
                {description && (
                  <span className="mt-0.5 block text-[9px] leading-snug text-gray-400">
                    {description}
                  </span>
                )}
                {fieldState.reason && (
                  <span className="mt-0.5 block text-[9px] leading-snug text-amber-600 dark:text-amber-400">
                    {fieldState.reason}
                  </span>
                )}
                <FieldHint prop={prop} />
              </span>
            </label>
          );
        }

        if (options) {
          return (
            <div key={key} className={disabledClass}>
              <label className="mb-0.5 block text-[10px] font-medium text-gray-600 dark:text-gray-300">
                {label}
              </label>
              {description && (
                <p className="mb-0.5 text-[9px] leading-snug text-gray-400">
                  {description}
                </p>
              )}
              {fieldState.reason && (
                <p className="mb-0.5 text-[9px] leading-snug text-amber-600 dark:text-amber-400">
                  {fieldState.reason}
                </p>
              )}
              <FieldHint prop={prop} />
              <select
                value={String(values[key] ?? "")}
                disabled={fieldState.disabled}
                onChange={(e) => setValue(key, e.target.value)}
                className={cn(compactInputClass, "mt-0.5")}
              >
                <option value="">Use default</option>
                {options.map((opt) => (
                  <option key={String(opt)} value={String(opt)}>
                    {String(opt)}
                  </option>
                ))}
              </select>
            </div>
          );
        }

        return (
          <div key={key} className={disabledClass}>
            <label className="mb-0.5 block text-[10px] font-medium text-gray-600 dark:text-gray-300">
              {label}
            </label>
            {description && (
              <p className="mb-0.5 text-[9px] leading-snug text-gray-400">
                {description}
              </p>
            )}
            {fieldState.reason && (
              <p className="mb-0.5 text-[9px] leading-snug text-amber-600 dark:text-amber-400">
                {fieldState.reason}
              </p>
            )}
            <FieldHint prop={prop} />
            <input
              value={String(values[key] ?? "")}
              disabled={fieldState.disabled}
              onChange={(e) => setValue(key, e.target.value)}
              type={type === "integer" || type === "number" ? "number" : "text"}
              placeholder={placeholder}
              className={cn(compactInputClass, "mt-0.5")}
            />
          </div>
        );
      })}
    </div>
  );
}
