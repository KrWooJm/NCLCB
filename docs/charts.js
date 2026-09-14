/* 최소한의 SVG 차트 헬퍼 — 외부 라이브러리 없이 동작한다. */

const NS = 'http://www.w3.org/2000/svg';
const el = (tag, attrs = {}) => {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  return n;
};

let tipEl = null;
function tip() {
  if (!tipEl) {
    tipEl = document.createElement('div');
    tipEl.className = 'tip';
    document.body.appendChild(tipEl);
  }
  return tipEl;
}
/** 마크에 호버 툴팁을 붙인다. 히트 영역은 마크보다 크게 잡는다. */
export function hoverable(node, html) {
  node.style.cursor = 'default';
  node.addEventListener('mouseenter', (e) => {
    const t = tip(); t.innerHTML = html; t.classList.add('on');
    move(e);
  });
  node.addEventListener('mousemove', move);
  node.addEventListener('mouseleave', () => tip().classList.remove('on'));
  function move(e) {
    const t = tip();
    const pad = 14;
    let x = e.clientX + pad, y = e.clientY + pad;
    const r = t.getBoundingClientRect();
    if (x + r.width > window.innerWidth - 8) x = e.clientX - r.width - pad;
    if (y + r.height > window.innerHeight - 8) y = e.clientY - r.height - pad;
    t.style.left = `${x}px`; t.style.top = `${y}px`;
  }
}

const css = (name) => getComputedStyle(document.body).getPropertyValue(name).trim();

/**
 * 번호별 출현 횟수 막대 + 기대선 + ±2σ 밴드.
 * 밴드 안에 대부분이 들어오면 '편향 없음'이 시각적으로 드러난다.
 */
export function frequencyChart(mount, { counts, expected, sigma }) {
  const W = 900, H = 260, ML = 44, MR = 12, MT = 16, MB = 30;
  const iw = W - ML - MR, ih = H - MT - MB;
  const hi = Math.max(...counts, expected + 3 * sigma);
  const lo = Math.max(0, Math.min(...counts, expected - 3 * sigma) - 8);
  const y = (v) => MT + ih - ((v - lo) / (hi - lo)) * ih;
  const bw = iw / counts.length;

  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, width: '100%',
    role: 'img', 'aria-label': '번호별 출현 횟수' });

  // ±2σ 밴드 — 기대 범위
  svg.appendChild(el('rect', { x: ML, y: y(expected + 2 * sigma), width: iw,
    height: Math.abs(y(expected - 2 * sigma) - y(expected + 2 * sigma)),
    fill: css('--accent'), opacity: '.07' }));

  [lo, expected, hi].forEach((v) => {
    const yy = y(v);
    svg.appendChild(el('line', { x1: ML, x2: W - MR, y1: yy, y2: yy,
      stroke: css('--grid'), 'stroke-width': 1 }));
    const t = el('text', { x: ML - 8, y: yy + 4, 'text-anchor': 'end',
      fill: css('--text-3'), 'font-size': 11 });
    t.textContent = Math.round(v);
    svg.appendChild(t);
  });

  counts.forEach((c, i) => {
    const x = ML + i * bw;
    const top = y(c);
    const bar = el('rect', { x: x + bw * 0.18, y: top, width: bw * 0.64,
      height: Math.max(1, MT + ih - top), rx: 3, fill: css('--series-1') });
    const dev = (c - expected) / sigma;
    hoverable(bar, `<b>${i + 1}번</b> · ${c}회 출현<br>기대치 대비 ${dev >= 0 ? '+' : ''}${dev.toFixed(1)}σ`);
    svg.appendChild(bar);
    if ((i + 1) % 5 === 0 || i === 0) {
      const t = el('text', { x: x + bw / 2, y: H - 9, 'text-anchor': 'middle',
        fill: css('--text-3'), 'font-size': 11 });
      t.textContent = i + 1;
      svg.appendChild(t);
    }
  });

  // 기대선은 마크 위에 그려 항상 읽히게 한다
  svg.appendChild(el('line', { x1: ML, x2: W - MR, y1: y(expected), y2: y(expected),
    stroke: css('--series-2'), 'stroke-width': 2, 'stroke-dasharray': '5 4' }));

  mount.replaceChildren(svg);
}

/** 관측 vs 이론 그룹 막대. series: [{name,color,values}] */
export function groupedBars(mount, { labels, series, fmt = (v) => v.toFixed(0) }) {
  const W = 900, H = 250, ML = 48, MR = 12, MT = 14, MB = 34;
  const iw = W - ML - MR, ih = H - MT - MB;
  const hi = Math.max(...series.flatMap((s) => s.values)) * 1.12 || 1;
  const y = (v) => MT + ih - (v / hi) * ih;
  const gw = iw / labels.length;
  const bw = (gw * 0.68) / series.length;

  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, width: '100%', role: 'img' });
  for (let i = 0; i <= 4; i++) {
    const v = (hi / 4) * i, yy = y(v);
    svg.appendChild(el('line', { x1: ML, x2: W - MR, y1: yy, y2: yy,
      stroke: css('--grid'), 'stroke-width': 1 }));
    const t = el('text', { x: ML - 8, y: yy + 4, 'text-anchor': 'end',
      fill: css('--text-3'), 'font-size': 11 });
    t.textContent = fmt(v);
    svg.appendChild(t);
  }
  labels.forEach((lab, gi) => {
    const gx = ML + gi * gw + gw * 0.16;
    series.forEach((s, si) => {
      const v = s.values[gi];
      const top = y(v);
      // 인접 막대 사이 2px 면 간격
      const bar = el('rect', { x: gx + si * bw + 1, y: top, width: bw - 2,
        height: Math.max(1, MT + ih - top), rx: 4, fill: s.color });
      hoverable(bar, `<b>${lab}</b><br>${s.name}: ${fmt(v)}`);
      svg.appendChild(bar);
    });
    const t = el('text', { x: ML + gi * gw + gw / 2, y: H - 11, 'text-anchor': 'middle',
      fill: css('--text-2'), 'font-size': 11 });
    t.textContent = lab;
    svg.appendChild(t);
  });
  mount.replaceChildren(svg);
}

/** 가로 막대 — 하나의 측정값을 그룹별로 비교한다. 길이가 크기를, 그룹 헤더가 맥락을 담당한다. */
export function barsH(mount, { rows, color, fmt = (v) => v.toFixed(2), unit = '' }) {
  const rowH = 40, headH = 28, W = 900, ML = 215, MR = 76;
  const bars = rows.filter((r) => !r.group);
  const hi = Math.max(...bars.map((r) => r.value)) * 1.12 || 1;
  const iw = W - ML - MR;
  const H = rows.reduce((h, r) => h + (r.group ? headH : rowH), 14);
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, width: '100%', role: 'img' });

  let yy = 8;
  rows.forEach((r) => {
    if (r.group) {
      const g = el('text', { x: 0, y: yy + 19, fill: css('--text-3'),
        'font-size': 11.5, 'font-weight': 700 });
      g.textContent = r.group;
      svg.appendChild(g);
      svg.appendChild(el('line', { x1: 0, x2: W, y1: yy + 26, y2: yy + 26,
        stroke: css('--grid'), 'stroke-width': 1 }));
      yy += headH;
      return;
    }
    const w = Math.max(2, (r.value / hi) * iw);
    const lab = el('text', { x: ML - 12, y: yy + 19, 'text-anchor': 'end',
      fill: css('--text-2'), 'font-size': 12.5 });
    lab.textContent = r.label;
    svg.appendChild(lab);
    const bar = el('rect', { x: ML, y: yy + 4, width: w, height: 22, rx: 4, fill: color });
    hoverable(bar, `<b>${r.label}</b><br>${fmt(r.value)}${unit}<br>표본 ${r.n}회차`);
    svg.appendChild(bar);
    const val = el('text', { x: ML + w + 9, y: yy + 20, fill: css('--text'),
      'font-size': 12, 'font-weight': 600 });
    val.textContent = fmt(r.value) + unit;
    svg.appendChild(val);
    yy += rowH;
  });
  mount.replaceChildren(svg);
}
