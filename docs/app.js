import { TIER_ODDS, P_ANY_PRIZE, TICKET_PRICE, MAX_NUM, PICK } from './engine.js';
import { analyse, popularity, backtest, generate, features, FILTERS } from './analysis.js';
import { frequencyChart, groupedBars, barsH } from './charts.js';

const $ = (s) => document.querySelector(s);
const fmtInt = (n) => Math.round(n).toLocaleString('ko-KR');
const pct = (v, d = 2) => `${(v * 100).toFixed(d)}%`;
const ballClass = (n) => `b${Math.min(5, Math.floor((n - 1) / 10) + 1)}`;

const DATA = window.__LOTTO_DATA__ || { draws: [], latestRound: 0 };
const DRAWS = DATA.draws || [];

/* ── 테마 토글 ─────────────────────────────────────────── */
const savedTheme = (() => { try { return localStorage.getItem('theme'); } catch { return null; } })();
if (savedTheme) document.documentElement.dataset.theme = savedTheme;
$('#theme').addEventListener('click', () => {
  const dark = document.documentElement.dataset.theme === 'dark'
    || (!document.documentElement.dataset.theme
      && matchMedia('(prefers-color-scheme: dark)').matches);
  const next = dark ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('theme', next); } catch { /* 저장 불가해도 동작 */ }
  renderCharts();
});

/* 데이터가 아직 수집되지 않은 상태 */
if (!DRAWS.length) {
  $('#app').innerHTML = `<div class="card"><h2>데이터를 수집하는 중입니다</h2>
    <p class="note">GitHub Actions 워크플로 <span class="mono">update-lotto.yml</span> 이
    한 번 실행되면 1회차부터 최신 회차까지 자동으로 채워집니다.
    저장소의 Actions 탭에서 <b>Run workflow</b> 를 눌러 즉시 실행할 수 있습니다.</p></div>`;
  throw new Error('no data');
}

const STATS = analyse(DRAWS);
const POP = popularity(DRAWS);
const latest = DRAWS[DRAWS.length - 1];

/* ── 헤더 ──────────────────────────────────────────────── */
$('#round-badge').textContent = `최신 ${latest.no}회 (${latest.date}) · 다음 ${latest.no + 1}회 분석 반영`;
$('#updated').textContent = DATA.updatedAt
  ? new Date(DATA.updatedAt).toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' })
  : '-';

$('#latest-numbers').innerHTML = latest.numbers
  .map((n) => `<span class="ball ${ballClass(n)}">${n}</span>`).join('')
  + `<span style="color:var(--text-3);margin:0 4px">+</span>`
  + `<span class="ball ${ballClass(latest.bonus)}">${latest.bonus}</span>`;

/* ── 현실 계산 타일 ────────────────────────────────────── */
function renderReality(games) {
  const spend = games * TICKET_PRICE;
  const pAny = 1 - (1 - P_ANY_PRIZE) ** games;
  const pFirst = 1 - (1 - TIER_ODDS[1]) ** games;
  // 기대 회수액: 4·5등은 고정 당첨금, 1~3등은 과거 평균 당첨금 사용
  const avgFirst = DRAWS.filter((d) => d.firstPrize > 0)
    .reduce((s, d, _, a) => s + d.firstPrize / a.length, 0);
  const ev = games * (TIER_ODDS[5] * 5000 + TIER_ODDS[4] * 50000
    + TIER_ODDS[3] * 1500000 + TIER_ODDS[2] * 60000000 + TIER_ODDS[1] * avgFirst);
  $('#reality').innerHTML = `
    <div class="tile"><div class="k">구매 금액</div><div class="v">${fmtInt(spend)}원</div>
      <div class="d">${games}게임 × ${fmtInt(TICKET_PRICE)}원</div></div>
    <div class="tile"><div class="k">5등 이상 1회 이상 당첨</div>
      <div class="v">${pct(pAny, 1)}</div><div class="d">대부분 5,000원짜리 5등입니다</div></div>
    <div class="tile"><div class="k">1등 당첨 확률</div>
      <div class="v">${pct(pFirst, 5)}</div>
      <div class="d">약 ${fmtInt(1 / (TIER_ODDS[1] * games))}주에 1번 꼴</div></div>
    <div class="tile"><div class="k">기대 회수액</div>
      <div class="v" style="color:var(--crit)">${fmtInt(ev)}원</div>
      <div class="d">투입액의 약 ${Math.round((ev / spend) * 100)}% — 구조적 손실입니다</div></div>`;
}

/* ── 필터 토글 ─────────────────────────────────────────── */
$('#toggles').innerHTML = FILTERS.map((f) => `
  <label class="toggle">
    <input type="checkbox" data-filter="${f.id}" checked>
    <span><span class="tl">${f.label}</span>
      <span class="chip ${f.effect}">${f.effect === 'payout' ? '기대 수령액 ↑' : '확률 영향 없음'}</span>
      <span class="tw">${f.why}</span></span>
  </label>`).join('');

/* ── 번호 생성 ─────────────────────────────────────────── */
function runGenerate() {
  const games = Math.max(1, Math.min(200,
    Math.floor(Number($('#budget').value || 50000) / TICKET_PRICE)));
  const opts = {};
  document.querySelectorAll('[data-filter]').forEach((c) => { opts[c.dataset.filter] = c.checked; });
  const seedRaw = $('#seed').value.trim();
  const seed = seedRaw ? [...seedRaw].reduce((a, c) => a * 31 + c.charCodeAt(0) | 0, 7)
    : (Date.now() & 0x7fffffff);

  const t0 = performance.now();
  const { tickets, usage } = generate({ games, opts, pastDraws: DRAWS, seed });
  const ms = Math.round(performance.now() - t0);

  $('#tickets').innerHTML = tickets.map((t, i) => `
    <div class="ticket"><span class="idx">${String(i + 1).padStart(2, '0')}</span>
      ${t.map((n) => `<span class="ball ${ballClass(n)}">${n}</span>`).join('')}</div>`).join('');

  const used = usage.slice(1);
  const cover = used.filter((u) => u > 0).length;
  $('#gen-summary').innerHTML = `
    <b>${games}게임</b> 생성 (${fmtInt(games * TICKET_PRICE)}원) · 45개 번호 중
    <b>${cover}개</b> 사용 · 번호별 ${Math.min(...used)}~${Math.max(...used)}회 등장 ·
    게임 간 중복 최대 ${maxOverlap(tickets)}개 · ${ms}ms`;
  renderReality(games);
  window.__TICKETS__ = tickets;
}
function maxOverlap(ts) {
  let m = 0;
  for (let i = 0; i < ts.length; i++) {
    for (let j = i + 1; j < ts.length; j++) {
      const o = ts[i].filter((x) => ts[j].includes(x)).length;
      if (o > m) m = o;
    }
  }
  return m;
}
$('#go').addEventListener('click', runGenerate);
$('#copy').addEventListener('click', async () => {
  const txt = (window.__TICKETS__ || []).map((t, i) =>
    `${String(i + 1).padStart(2, '0')}  ${t.map((n) => String(n).padStart(2, '0')).join(' ')}`).join('\n');
  try {
    await navigator.clipboard.writeText(txt);
    $('#copy').textContent = '복사됨';
    setTimeout(() => { $('#copy').textContent = '번호 복사'; }, 1400);
  } catch { alert(txt); }
});

/* ── 통계 요약 ─────────────────────────────────────────── */
const u = STATS.uniformity;
const verdict = u.p > 0.05
  ? `<span class="ok">균등합니다 (p = ${u.p.toFixed(3)})</span>`
  : `<span class="bad">편향 신호 (p = ${u.p.toFixed(3)})</span>`;
$('#uniformity').innerHTML = `
  전 회차 ${fmtInt(STATS.n)}회, 번호 ${fmtInt(STATS.n * PICK)}개를 카이제곱 적합도 검정한 결과:
  <b>${verdict}</b>. 즉 <b>자주 나온 번호도, 오래 안 나온 번호도 다음 회차 확률은 똑같이 1/45</b> 입니다.
  아래 그래프의 막대가 파란 띠(±2σ) 안에 머무는 것이 그 근거입니다.`;

const sigma = Math.sqrt(STATS.n * PICK * (1 / MAX_NUM) * (1 - 1 / MAX_NUM));

/* 핫/콜드 표 — 예측력이 없음을 명시한 채로 제공 */
const byCount = [...STATS.drought].sort((a, b) => b.count - a.count);
const byGap = [...STATS.drought].sort((a, b) => b.gap - a.gap);
$('#hotcold').innerHTML = `
  <tr><td>최다 출현</td>${byCount.slice(0, 5).map((d) =>
    `<td>${d.num}번 <span style="color:var(--text-3)">(${d.count}회)</span></td>`).join('')}</tr>
  <tr><td>최소 출현</td>${byCount.slice(-5).reverse().map((d) =>
    `<td>${d.num}번 <span style="color:var(--text-3)">(${d.count}회)</span></td>`).join('')}</tr>
  <tr><td>최장 미출현</td>${byGap.slice(0, 5).map((d) =>
    `<td>${d.num}번 <span style="color:var(--text-3)">(${d.gap}회차)</span></td>`).join('')}</tr>`;

$('#carry').textContent = `${(STATS.carryOverRate * 100).toFixed(1)}%`;
$('#carry-theory').textContent = `이론값 66.1% — 실제로 성립하는 몇 안 되는 규칙이지만, `
  + `"어느 번호가" 재출현할지는 전혀 알려주지 않아 예측에 쓸 수 없습니다.`;

/* ── 인기도 분석 ───────────────────────────────────────── */
if (POP && POP.lift) {
  const l = POP.lift;
  const stronger = l.ratio > 1;
  $('#pop-summary').innerHTML = `
    1등 당첨자 수는 "그 조합을 몇 명이 샀는가"의 직접 관측치입니다.
    판매액으로 정규화해 ${fmtInt(POP.sampleSize)}회차를 비교하면,
    <b>1~31 안에서만 나온 당첨번호</b>의 1등 당첨자 수가
    32 이상을 포함한 경우의 <b class="${stronger ? 'bad' : 'ok'}">${l.ratio.toFixed(2)}배</b>
    입니다 (p = ${l.p < 0.001 ? '&lt;0.001' : l.p.toFixed(3)}).
    ${stronger && l.p < 0.05
      ? '생일 번호대에 구매가 몰린다는 뜻이고, 이것이 <b>32 이상 포함</b> 필터의 근거입니다. 당첨 확률은 그대로지만 당첨 시 나눠 갖는 인원이 줄어듭니다.'
      : '이번 데이터에서는 통계적으로 뚜렷하지 않습니다. 필터는 유지하되 효과를 과장하지 않습니다.'}`;
} else {
  $('#pop-summary').textContent = '인기도 분석에 필요한 판매액 데이터가 부족합니다.';
}

/* ── 백테스트 ──────────────────────────────────────────── */
const NAMES = {
  random: '순수 무작위 (기준선)', hot: '핫넘버 — 다출 번호 위주',
  cold: '콜드넘버 — 미출 번호 위주', exclude: '제외수 — 최근 다출 10개 제외',
  portfolio: '이 사이트 전략 (인기 회피)',
};
let BT = null;
function runBacktest() {
  $('#bt-status').textContent = '계산 중…';
  setTimeout(() => {
    BT = backtest(DRAWS, { ticketsPerDraw: 20, warmup: 100, seed: 7 });
    const theory = (PICK * PICK) / MAX_NUM;
    $('#bt-body').innerHTML = BT.map((r) => {
      const same = r.name === 'random' || r.p > 0.05;
      return `<tr>
        <td>${NAMES[r.name]}</td>
        <td>${r.mean.toFixed(4)}</td>
        <td>${r.name === 'random' ? '—' : (r.diff >= 0 ? '+' : '') + r.diff.toFixed(4)}</td>
        <td>${r.name === 'random' ? '—' : r.p.toFixed(3)}</td>
        <td>${pct(r.prizeRate, 3)}</td>
        <td class="verdict ${same ? 'ok' : 'bad'}">${r.name === 'random' ? '기준'
          : same ? '무작위와 차이 없음' : '차이 있음'}</td></tr>`;
    }).join('');
    $('#bt-status').innerHTML = `${fmtInt(BT[0].games)}게임 × 5전략 시뮬레이션 완료.
      이론 기대 적중 개수는 <b>${theory.toFixed(4)}</b>개이며, 모든 전략이 이 값 주변에 머뭅니다.
      p값이 0.05보다 크다는 것은 <b>무작위와 구별할 수 없다</b>는 뜻입니다.`;
  }, 20);
}
$('#bt-run').addEventListener('click', runBacktest);

/* ── 차트 렌더 ─────────────────────────────────────────── */
function renderCharts() {
  frequencyChart($('#chart-freq'), {
    counts: STATS.freq.slice(1), expected: STATS.expectedPerNumber, sigma,
  });

  // 홀수 개수 분포: 관측 vs 이론(초기하분포)
  const cOdd = (k) => {
    const C = (n, r) => { let x = 1; for (let i = 1; i <= r; i++) x = x * (n - r + i) / i; return x; };
    return (C(23, k) * C(22, PICK - k)) / C(45, PICK);
  };
  const theoryOdd = [0, 1, 2, 3, 4, 5, 6].map((k) => cOdd(k) * STATS.n);
  groupedBars($('#chart-odd'), {
    labels: ['0개', '1개', '2개', '3개', '4개', '5개', '6개'],
    series: [
      { name: '실제 관측', color: getComputedStyle(document.body).getPropertyValue('--series-1').trim(),
        values: STATS.oddCounts },
      { name: '확률 이론값', color: getComputedStyle(document.body).getPropertyValue('--series-2').trim(),
        values: theoryOdd },
    ],
  });

  if (POP) {
    const c1 = getComputedStyle(document.body).getPropertyValue('--series-1').trim();
    // 측정값이 하나(인기도)이므로 색은 하나만 쓰고, 맥락은 그룹 헤더가 담당한다.
    const rows = POP.groups.flatMap((g) => [{ group: g.label },
      ...g.rows.map((r) => ({ label: `${r.key}`, value: r.mean, n: r.n }))]);
    barsH($('#chart-pop'), { rows, color: c1, fmt: (v) => v.toFixed(2), unit: '명' });
  }
}

/* 초기 구동 */
renderCharts();
runGenerate();
addEventListener('resize', () => { /* viewBox 기반이라 재계산 불필요 */ });
