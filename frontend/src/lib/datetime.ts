const TZ_SUFFIX_RE = /[zZ]|[+-]\d{2}:\d{2}$/;

export function normalizeUtcTimestamp(value: string): string {
  if (TZ_SUFFIX_RE.test(value)) {
    return value;
  }
  return `${value.replace(" ", "T")}Z`;
}

export function parseDateWithUtcFallback(value: string): Date {
  const normalized = normalizeUtcTimestamp(value);
  const date = new Date(normalized);
  if (!Number.isNaN(date.getTime())) {
    return date;
  }
  return new Date(value);
}
