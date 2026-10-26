import type { PatternVariant, ReportPattern } from "../../types/report";

const roleLabels = { context: "Context", signal: "Signal", measured: "Measured", termination: "Ends the run" };
const pixel = (value: number) => Number(value.toFixed(2));
const symbolId = (reportId: string, patternId: string, variantId: string) => `pattern-symbol-${[reportId, patternId, variantId].map(value => `${value.length}-${value}`).join("-")}`;

function labelLines(label: string, maxCharacters: number) {
  const words = label.split(/\s+/).flatMap(word => word.match(new RegExp(`.{1,${maxCharacters}}`, "g")) ?? []);
  const lines: string[] = [];
  for (const word of words) {
    const previous = lines.at(-1);
    if (previous && previous.length + word.length + 1 <= maxCharacters) {
      lines[lines.length - 1] = `${previous} ${word}`;
    } else {
      lines.push(word);
    }
  }
  return lines.length ? lines : [label];
}

function layout(variant: PatternVariant) {
  const step = 36;
  const labels = variant.candles.map(candle => labelLines(candle.label, 4));
  const extraLabelHeight = (Math.max(...labels.map(lines => lines.length)) - 1) * 19;
  const spans = (variant.marks ?? []).filter(mark => mark.kind === "span");
  const prices = variant.candles.flatMap(candle => [candle.open, candle.high, candle.low, candle.close]);
  for (const mark of variant.marks ?? []) {
    if (mark.kind === "level") prices.push(mark.price);
    if (mark.kind === "band") prices.push(mark.low, mark.high);
  }
  const lowest = Math.min(...prices);
  const highest = Math.max(...prices);
  const padding = Math.max(4, (highest - lowest) * 0.12);
  return { step, labels, extraLabelHeight, spans, minimum: lowest - padding, maximum: highest + padding, height: 238 + extraLabelHeight + spans.length * 22 };
}

function PatternGeometry({ variant }: { variant: PatternVariant }) {
  const { step, labels, extraLabelHeight, spans, minimum, maximum } = layout(variant);
  const x = (index: number) => pixel(260 + step * (index - (variant.candles.length - 1) / 2));
  const y = (price: number) => pixel(26 + (maximum - price) / (maximum - minimum) * 165);
  const width = 12;
  const marks = variant.marks ?? [];
  const levels = marks.flatMap((mark, index) => mark.kind === "level" ? [{ index, position: y(mark.price) }] : []).sort((a, b) => a.position - b.position);
  for (let index = 1; index < levels.length; index += 1) {
    levels[index].position = Math.max(levels[index].position, levels[index - 1].position + 18);
  }
  const labelOverflow = Math.max(0, (levels.at(-1)?.position ?? 0) - 196);
  const levelLabels = new Map(levels.map(level => [level.index, pixel(level.position - labelOverflow)]));
  const bands = marks.flatMap((mark, index) => mark.kind === "band" ? [{ index, position: pixel((y(mark.high) + y(mark.low)) / 2) }] : []).sort((a, b) => a.position - b.position);
  for (let index = 1; index < bands.length; index += 1) {
    bands[index].position = Math.max(bands[index].position, bands[index - 1].position + 18);
  }
  const bandOverflow = Math.max(0, (bands.at(-1)?.position ?? 0) - 196);
  const bandLabels = new Map(bands.map(band => [band.index, pixel(band.position - bandOverflow)]));
  return <>
    {marks.map((mark, index) => {
      if (mark.kind !== "band") return null;
      const left = pixel(x(variant.candles.findIndex(candle => candle.id === mark.startCandle)) - step * 0.44);
      const right = pixel(x(variant.candles.findIndex(candle => candle.id === mark.endCandle)) + step * 0.44);
      return <g key={`band-${index}`} className="pattern-band">
        <rect x={left} y={y(mark.high)} width={pixel(right - left)} height={pixel(y(mark.low) - y(mark.high))} />
        <path className="pattern-band-leader" d={`M 26 ${bandLabels.get(index)} H 30 V ${pixel((y(mark.high) + y(mark.low)) / 2)} H ${left}`} />
      </g>;
    })}
    {variant.candles.map((candle, index) => {
      const middle = x(index);
      const bodyTop = y(Math.max(candle.open, candle.close));
      const bodyHeight = pixel(Math.max(2, Math.abs(y(candle.open) - y(candle.close))));
      const direction = candle.close > candle.open ? "up" : candle.close < candle.open ? "down" : "flat";
      return <g key={candle.id} className={`pattern-candle candle-${direction} role-${candle.role}`}>
        <title>{`${candle.label}: ${roleLabels[candle.role]}, ${direction === "up" ? "rising" : direction === "down" ? "falling" : "flat"} candle`}</title>
        {candle.role === "measured" ? <rect className="pattern-measured-area" x={pixel(middle - step * 0.43)} y="14" width={pixel(step * 0.86)} height="187" rx="3" /> : null}
        <line className="pattern-wick" x1={middle} y1={y(candle.high)} x2={middle} y2={y(candle.low)} />
        <rect className="pattern-body" x={pixel(middle - width / 2)} y={bodyTop} width={width} height={bodyHeight} rx="1" />
        {candle.role === "signal" ? <path className="pattern-signal-marker" d={`M ${middle} 194 l -4 7 h 8 z`} /> : null}
        <text className="pattern-candle-label" x={middle} y="216">{labels[index].map((line, lineIndex) => <tspan key={lineIndex} x={middle} dy={lineIndex ? 19 : 0}>{line}</tspan>)}</text>
      </g>;
    })}
    {marks.map((mark, index) => {
      const left = pixel(x(variant.candles.findIndex(candle => candle.id === mark.startCandle)) - width / 2);
      const right = pixel(x(variant.candles.findIndex(candle => candle.id === mark.endCandle)) + width / 2);
      if (mark.kind === "band") return <g className="pattern-band-callout" key={`band-callout-${index}`}>
        <text x="16" y={pixel((bandLabels.get(index) ?? 26) + 5)}>{index + 1}</text>
      </g>;
      if (mark.kind === "level") return <g className="pattern-level" key={`level-${index}`}>
        <line x1={left} y1={y(mark.price)} x2={right} y2={y(mark.price)} />
        <path className="pattern-level-leader" d={`M ${right} ${y(mark.price)} H 486 V ${levelLabels.get(index)} H 494`} />
        <text x="505" y={pixel((levelLabels.get(index) ?? y(mark.price)) + 5)}>{index + 1}</text>
      </g>;
      if (mark.kind !== "span") return null;
      const baseline = 236 + extraLabelHeight + spans.indexOf(mark) * 22;
      return <g className="pattern-span" key={`span-${index}`}>
        <path d={`M ${left} ${baseline - 5} v 5 H ${right} v -5`} />
        <text x={pixel((left + right) / 2)} y={baseline + 14}>{index + 1}</text>
      </g>;
    })}
  </>;
}

export function PatternDefinitions({ patterns, reportId }: { patterns: ReportPattern[]; reportId: string }) {
  return <svg className="pattern-definitions" width="0" height="0" aria-hidden="true" focusable="false"><defs>
    {patterns.flatMap(pattern => pattern.variants.map(variant => <symbol key={`${pattern.id}/${variant.id}`} id={symbolId(reportId, pattern.id, variant.id)} viewBox={`0 0 520 ${layout(variant).height}`}><PatternGeometry variant={variant} /></symbol>))}
  </defs></svg>;
}

function PatternDrawing({ variant, instanceId, symbol, compact, explanationId }: { variant: PatternVariant; instanceId: string; symbol?: string; compact: boolean; explanationId: string }) {
  const marks = variant.marks ?? [];
  return <figure className="pattern-variant">
    <h4>{variant.title}</h4>
    <svg viewBox={`0 0 520 ${layout(variant).height}`} role="img" aria-labelledby={`${instanceId}-title ${instanceId}-description`} aria-describedby={compact ? `${explanationId}-${variant.id}-key` : undefined} className="pattern-drawing">
      <title id={`${instanceId}-title`}>{`${variant.title}: illustrative candle pattern`}</title>
      <desc id={`${instanceId}-description`}>{compact ? "Measured candles are shaded; the full pattern key explains the numbered marks and candle roles." : `${variant.description} Shaded columns identify measured candles. Outlined candles with a triangle identify the signal; dashed candles end the run. Unmarked candles show context. Green candles close above their open; purple candles close below. This is a schematic, not an observed price sample.`}</desc>
      {symbol ? <use href={`#${symbol}`} /> : <PatternGeometry variant={variant} />}
    </svg>
    {!compact ? <figcaption id={`${explanationId}-${variant.id}-key`}>
      <p>{variant.description}</p>
      {marks.length ? <ol className="pattern-mark-key">{marks.map((mark, index) => <li key={index}><span aria-hidden="true">{index + 1}</span>{mark.label}</li>)}</ol> : null}
    </figcaption> : null}
  </figure>;
}

export function PatternPanel({ pattern, instanceId, focus, overview = false, symbolReportId, compact = false }: { pattern: ReportPattern; instanceId: string; focus?: string; overview?: boolean; symbolReportId?: string; compact?: boolean }) {
  const roles = [...new Set(pattern.variants.flatMap(variant => variant.candles.map(candle => candle.role)))];
  const explanationId = `pattern-key-${pattern.id}`;
  const focusText = focus?.replace(/^This section measures\s+/, "");
  return <aside id={compact ? undefined : explanationId} className={`pattern-panel${overview ? " pattern-overview" : ""}${compact ? " pattern-compact" : ""}`} aria-labelledby={`${instanceId}-heading`}>
    <div className="pattern-panel-heading"><h3 id={`${instanceId}-heading`}>{pattern.title}</h3><span>Illustrative schematic</span></div>
    {!compact ? <p className="pattern-description">{pattern.description}</p> : null}
    {focusText ? <p className="pattern-focus"><strong>This section measures:</strong> {focusText}</p> : null}
    <div className={`pattern-variants${pattern.variants.length === 2 ? " pattern-variants-pair" : ""}`}>
      {pattern.variants.map(variant => <PatternDrawing key={variant.id} variant={variant} instanceId={`${instanceId}-${variant.id}`} symbol={symbolReportId ? symbolId(symbolReportId, pattern.id, variant.id) : undefined} compact={compact} explanationId={explanationId} />)}
    </div>
    {compact ? <a className="pattern-key-link" href={`#${explanationId}`}>Pattern key and definitions</a> : <ul className="pattern-role-key" aria-label="Candle role key">{roles.map(role => <li key={role} className={`key-${role}`}><span aria-hidden="true" />{roleLabels[role]}</li>)}</ul>}
  </aside>;
}
