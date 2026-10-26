// Selected evidence only. This module parses a bounded CSV, never research data.
export function validateReferenceUrl(value) {
  if (value !== value.trim() || /[\s\\\u0000-\u001f\u007f]/u.test(value)) throw new Error('Reference URL must be a clean HTTPS URL.');
  let url;
  try { url = new URL(value); } catch { throw new Error('Reference URL must be a valid HTTPS URL.'); }
  if (url.protocol !== 'https:' || url.username || url.password || url.port ||
      !/^[a-z0-9.-]+\.[a-z]{2,63}$/i.test(url.hostname) || /\.(?:local|internal|localhost|test)$/i.test(url.hostname)) {
    throw new Error('Reference URL must use public HTTPS without credentials or a custom port.');
  }
  return value;
}

export function validateCsv(bytes, declaration) {
  let text;
  try { text = new TextDecoder('utf-8', { fatal: true }).decode(bytes); } catch { throw new Error('Download must be UTF-8 CSV.'); }
  if (!text || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/u.test(text)) throw new Error('CSV contains forbidden control characters.');
  const rows = []; let row = [], field = '', quoted = false, closed = false;
  const pushField = () => {
    if (field.length > 1000) throw new Error('CSV cell exceeds 1000 characters.');
    // Preserve signed numbers while excluding spreadsheet formula payloads.
    if (/^\s*[=+@-]/u.test(field) && !/^\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\s*$/u.test(field)) throw new Error('CSV formula cells are not permitted.');
    row.push(field); field = ''; closed = false;
  };
  const pushRow = () => { pushField(); rows.push(row); row = []; if (rows.length > 1001) throw new Error('CSV exceeds 1000 data rows.'); };
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (ch === '"') { quoted = false; closed = true; }
      else field += ch;
    } else if (ch === '"') {
      if (field || closed) throw new Error('Malformed CSV quoting.');
      quoted = true;
    } else if (ch === ',') pushField();
    else if (ch === '\n' || ch === '\r') { if (ch === '\r' && text[i + 1] === '\n') i++; pushRow(); }
    else { if (closed) throw new Error('Malformed CSV after a quoted cell.'); field += ch; }
  }
  if (quoted) throw new Error('Unterminated CSV quote.');
  if (field || row.length || closed) pushRow();
  if (JSON.stringify(rows[0]) !== JSON.stringify(declaration.columns)) throw new Error('CSV headers do not match declared columns.');
  if (rows.length - 1 !== declaration.rowCount) throw new Error('CSV row count does not match its declaration.');
  if (rows.some(r => r.length !== declaration.columns.length)) throw new Error('CSV rows have inconsistent widths.');
  return rows;
}
