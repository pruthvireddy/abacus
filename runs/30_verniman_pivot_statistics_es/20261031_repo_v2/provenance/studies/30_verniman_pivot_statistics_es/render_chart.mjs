// Presentation only: rasterize precomputed saved means and confidence bounds.
import { createRequire } from 'node:module';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const finite = value => typeof value === 'number' && Number.isFinite(value);
const labels = {
  same_close_actual_crossing: 'EMA6 crossed at the same close',
  already_aligned: 'EMA6 was already on the break side',
  opposite: 'EMA6 remained on the opposite side',
  equal_with_remembered_side: 'EMA6 equaled the pivot',
  unavailable_uninitialized: 'EMA6 unavailable or uninitialized',
};
const signed = value => `${value > 0 ? '+' : ''}${value.toFixed(2)}`;

export function buildSvg(input) {
  if (!Array.isArray(input.rows) || input.rows.length > 12) throw new Error('A bounded saved-row array is required.');
  for (const row of input.rows) {
    for (const key of ['mean_points', 'mean_ci95_low', 'mean_ci95_high']) {
      if (row[key] !== null && !finite(row[key])) throw new Error(`Invalid saved chart number: ${key}`);
    }
    if (!Number.isInteger(row.denominator) || !Number.isInteger(row.valid_days)) throw new Error('Saved event and day counts are required.');
    if (finite(row.mean_ci95_low) && finite(row.mean_ci95_high) && row.mean_ci95_low > row.mean_ci95_high) throw new Error('Reversed saved interval.');
  }
  const width = 1440, height = Math.max(660, 330 + input.rows.length * 104);
  const left = 410, right = 1010, top = 192, bottom = height - 170;
  const values = [0, ...input.rows.flatMap(row => [row.mean_points, row.mean_ci95_low, row.mean_ci95_high]).filter(finite)];
  let low = Math.min(...values), high = Math.max(...values);
  const padding = Math.max((high - low) * .15, .15);
  low -= padding; high += padding;
  const x = value => left + (value - low) / (high - low) * (right - left);
  const parts = [`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
    '<title>Price breaks: EMA6 state known at the close</title>',
    '<desc>Saved mean signed 30-minute ES-point displacement with 95% day-block intervals, event counts and distinct-day support. Negative values remain negative. No trading profitability claim.</desc>',
    `<rect width="${width}" height="${height}" fill="#f7f9fc"/>`,
    '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#193048}.title{font-size:30px;font-weight:700}.sub{font-size:18px;fill:#52677d}.label{font-size:19px}.value{font-size:23px;font-weight:700}.detail{font-size:16px;fill:#52677d}.tick{font-size:16px;fill:#52677d}</style>',
    '<text class="title" x="42" y="54">Price breaks: EMA6 state known at the close</text>',
    `<text class="sub" x="42" y="88">Mean signed ES points after 30 minutes · all price crosses · ${escape(input.eligible_days)} eligible sessions</text>`,
    `<text class="sub" x="42" y="118">Observed sample ${escape(input.actual_start)}–${escape(input.actual_end)} · requested cutoff ${escape(input.requested_cutoff)}</text>`];
  for (let i = 0; i <= 5; i++) {
    const value = low + (high - low) * i / 5;
    parts.push(`<line x1="${x(value)}" x2="${x(value)}" y1="${top - 36}" y2="${bottom}" stroke="#dbe3ed"/>`,
      `<text class="tick" text-anchor="middle" x="${x(value)}" y="${bottom + 28}">${escape(signed(value))}</text>`);
  }
  parts.push(`<line x1="${x(0)}" x2="${x(0)}" y1="${top - 36}" y2="${bottom}" stroke="#60788f" stroke-width="2"/>`);
  input.rows.forEach((row, i) => {
    const y = top + i * 104;
    const label = labels[row.condition_value] ?? row.condition_value.replaceAll('_', ' ');
    parts.push(`<text class="label" x="42" y="${y + 7}">${escape(label)}</text>`);
    if (finite(row.mean_points)) {
      const a = Math.min(x(0), x(row.mean_points)), b = Math.max(x(0), x(row.mean_points));
      parts.push(`<rect data-state="${escape(row.condition_value)}" data-mean="${row.mean_points}" x="${a}" y="${y - 17}" width="${Math.max(1, b - a)}" height="34" rx="4" fill="${row.mean_points < 0 ? '#9a6376' : '#356e91'}"/>`);
      if (finite(row.mean_ci95_low) && finite(row.mean_ci95_high)) {
        parts.push(`<line x1="${x(row.mean_ci95_low)}" x2="${x(row.mean_ci95_high)}" y1="${y}" y2="${y}" stroke="#172b42" stroke-width="3"/>`,
          ...[row.mean_ci95_low, row.mean_ci95_high].map(value => `<line x1="${x(value)}" x2="${x(value)}" y1="${y - 9}" y2="${y + 9}" stroke="#172b42" stroke-width="3"/>`));
      }
      parts.push(`<text class="value" x="1050" y="${y - 3}">${escape(signed(row.mean_points))} points</text>`);
    } else parts.push(`<text class="value" x="1050" y="${y - 3}">Unavailable</text>`);
    parts.push(`<text class="detail" x="1050" y="${y + 22}">n=${row.denominator} · ${row.valid_days} distinct days</text>`,
      `<text class="detail" x="1050" y="${y + 46}">${finite(row.mean_ci95_low) && finite(row.mean_ci95_high) ? escape(`95% CI ${signed(row.mean_ci95_low)} to ${signed(row.mean_ci95_high)}`) : '95% interval unavailable'}</text>`);
  });
  parts.push(`<text class="detail" x="${left}" y="${bottom + 62}" text-anchor="start">Signed displacement in the price-crossing direction · ES points</text>`,
    `<text class="detail" x="42" y="${height - 68}">2,000 five-observed-session moving-block resamples; repeated events remain within their day.</text>`,
    `<text class="detail" x="42" y="${height - 42}">Historical pivot availability unverified · sparse if fewer than 30 days · fills, costs and net P&amp;L untested.</text>`, '</svg>');
  return parts.join('\n');
}

async function main() {
  const args = process.argv.slice(2), options = {};
  for (let i = 0; i < args.length; i += 2) {
    if (!['--input', '--output', '--app-package'].includes(args[i]) || !args[i + 1]) throw new Error('Usage: render_chart.mjs --input JSON --output PNG [--app-package package.json]');
    options[args[i].slice(2)] = args[i + 1];
  }
  if (!options.input || !options.output) throw new Error('Input and output paths are required.');
  const input = JSON.parse(await readFile(options.input, 'utf8'));
  const source = resolve(dirname(options.input), '..', input.artifact);
  const digest = createHash('sha256').update(await readFile(source)).digest('hex');
  if (digest !== input.sha256) throw new Error('Saved chart source hash changed.');
  const app = options['app-package'] ?? fileURLToPath(new URL('../../apps/narada/package.json', import.meta.url));
  const sharp = createRequire(resolve(app))('sharp');
  const svg = buildSvg(input);
  await writeFile(options.output.replace(/\.png$/, '.svg'), svg, { flag: 'wx' });
  await sharp(Buffer.from(svg)).png().toFile(options.output);
  process.stdout.write(JSON.stringify({ renderer: 'sharp-svg', node: process.version, versions: sharp.versions,
    source_sha256: digest, rows: input.rows.length, width: 1440, svg_sha256: createHash('sha256').update(svg).digest('hex') }) + '\n');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });
}
