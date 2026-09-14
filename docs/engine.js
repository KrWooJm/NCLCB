/* 로또 6/45 분석 엔진 — 순수 계산 모듈 (DOM 의존 없음) */

export const TOTAL_COMBOS = 8145060; // C(45,6)
export const PICK = 6;
export const MAX_NUM = 45;
export const TICKET_PRICE = 1000;

/* ── 조합론 ─────────────────────────────────────────────── */
export function comb(n, k) {
  if (k < 0 || k > n) return 0;
  let r = 1;
  for (let i = 1; i <= k; i++) r = (r * (n - k + i)) / i;
  return Math.round(r);
}

/** 한 게임의 등수별 당첨 확률. */
export const TIER_ODDS = (() => {
  const p = (m, bonus) => {
    if (m === 5 && bonus) return 6 / TOTAL_COMBOS;
    if (m === 5) return (comb(6, 5) * comb(38, 1)) / TOTAL_COMBOS;
    return (comb(6, m) * comb(39, 6 - m)) / TOTAL_COMBOS;
  };
  return {
    1: p(6, false), 2: p(5, true), 3: p(5, false), 4: p(4, false), 5: p(3, false),
  };
})();

export const P_ANY_PRIZE = Object.values(TIER_ODDS).reduce((a, b) => a + b, 0);

/* ── 통계 검정 ──────────────────────────────────────────── */

/** 정규화 상부 불완전감마 Q(a,x) — 카이제곱 p-value 계산용. */
function gammaQ(a, x) {
  if (x < 0 || a <= 0) return NaN;
  if (x === 0) return 1;
  const lg = lnGamma(a);
  if (x < a + 1) {
    // 급수 전개로 P(a,x) 를 구한 뒤 1 에서 뺀다
    let ap = a, sum = 1 / a, del = sum;
    for (let n = 0; n < 500; n++) {
      ap++; del *= x / ap; sum += del;
      if (Math.abs(del) < Math.abs(sum) * 1e-12) break;
    }
    return 1 - sum * Math.exp(-x + a * Math.log(x) - lg);
  }
  // 연분수 전개로 Q(a,x) 를 직접 구한다
  let b = x + 1 - a, c = 1e300, d = 1 / b, h = d;
  for (let i = 1; i < 500; i++) {
    const an = -i * (i - a);
    b += 2; d = an * d + b; if (Math.abs(d) < 1e-300) d = 1e-300;
    c = b + an / c; if (Math.abs(c) < 1e-300) c = 1e-300;
    d = 1 / d;
    const del = d * c; h *= del;
    if (Math.abs(del - 1) < 1e-12) break;
  }
  return h * Math.exp(-x + a * Math.log(x) - lg);
}

function lnGamma(z) {
  const g = [676.5203681218851, -1259.1392167224028, 771.32342877765313,
    -176.61502916214059, 12.507343278686905, -0.13857109526572012,
    9.9843695780195716e-6, 1.5056327351493116e-7];
  if (z < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * z)) - lnGamma(1 - z);
  z -= 1;
  let x = 0.99999999999980993;
  g.forEach((gi, i) => { x += gi / (z + i + 1); });
  const t = z + g.length - 0.5;
  return 0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(x);
}

/** 카이제곱 적합도 검정. 반환: { chi2, df, p } */
export function chiSquareTest(observed, expected) {
  let chi2 = 0;
  for (let i = 0; i < observed.length; i++) {
    const e = expected[i];
    chi2 += ((observed[i] - e) ** 2) / e;
  }
  const df = observed.length - 1;
  return { chi2, df, p: gammaQ(df / 2, chi2 / 2) };
}

/** 표준정규 누적분포 — 두 평균 비교의 p-value 용. */
function normCdf(z) {
  return 0.5 * (1 + erf(z / Math.SQRT2));
}
function erf(x) {
  const s = Math.sign(x); x = Math.abs(x);
  const t = 1 / (1 + 0.3275911 * x);
  const y = 1 - ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t
    - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
  return s * y;
}

/** 두 표본 평균 차이의 양측 z-검정. */
export function twoSampleZ(a, b) {
  const mean = (v) => v.reduce((s, x) => s + x, 0) / v.length;
  const varr = (v, m) => v.reduce((s, x) => s + (x - m) ** 2, 0) / (v.length - 1);
  const ma = mean(a), mb = mean(b);
  const se = Math.sqrt(varr(a, ma) / a.length + varr(b, mb) / b.length);
  if (!se) return { diff: 0, z: 0, p: 1 };
  const z = (ma - mb) / se;
  return { diff: ma - mb, z, p: 2 * (1 - normCdf(Math.abs(z))) };
}

/* ── 난수 (시드 고정 가능) ──────────────────────────────── */
export function makeRng(seed) {
  let s = seed >>> 0 || 1;
  return function rng() {
    s ^= s << 13; s >>>= 0;
    s ^= s >>> 17;
    s ^= s << 5; s >>>= 0;
    return s / 4294967296;
  };
}

/** 가중치 없는 단순 조합 추출. */
export function randomTicket(rng) {
  const pool = [];
  for (let i = 1; i <= MAX_NUM; i++) pool.push(i);
  for (let i = 0; i < PICK; i++) {
    const j = i + Math.floor(rng() * (pool.length - i));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  return pool.slice(0, PICK).sort((a, b) => a - b);
}
