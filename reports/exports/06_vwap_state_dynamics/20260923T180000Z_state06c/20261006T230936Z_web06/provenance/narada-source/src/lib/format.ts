export type NumberFormat = {
  format?: "number" | "percent";
  unit?: string;
  precision?: number;
};

/** Percent is an explicit ratio: 0.25 renders as 25%. Units never imply scaling. */
export function formatValue(value: unknown, options: NumberFormat = {}): string {
  if (value === null || value === undefined) return "Not available";
  if (typeof value !== "number") return String(value);
  if (!Number.isFinite(value)) return "Not available";
  const precision = options.precision ?? 2;
  const formatted = new Intl.NumberFormat("en-US", {
    style: options.format === "percent" ? "percent" : "decimal",
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  }).format(value);
  return options.unit ? `${formatted} ${options.unit}` : formatted;
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "long",
    timeZone: "UTC",
  }).format(new Date(value));
}
