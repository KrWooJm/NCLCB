/* 과거 데이터 분석 · 번호 생성 · 백테스트 */
import {
  MAX_NUM, PICK, TOTAL_COMBOS, chiSquareTest, twoSampleZ, makeRng, randomTicket,
} from './engine.js';

/* ── 조합의 특성 추출 ───────────────────────────────────── */
export function features(nums) {
  const sum = nums.reduce((a, b) => a + b, 0);
  const odd = nums.filter((n) => n % 2 === 1).length;
  const low31 = nums.filter((n) => n <= 31).length;   // 생일로 찍을 수 있는 범위
  const high = nums.filter((n) => n >= 32).length;
  const zones = [0, 0, 0, 0, 0];                       // 1-10 / 11-20 / 21-30 / 31-40 / 41-45
  nums.forEach((n) => { zones[Math.min(4, Math.floor((n - 1) / 10))]++; });

  let maxRun = 1, run = 1;
  for (let i = 1; i < nums.length; i++) {
    run = nums[i] === nums[i - 1] + 1 ? run + 1 : 1;
    if (run > maxRun) maxRun = run;
  }
  const tails = {};
  nums.forEach((n) => { tails[n % 10] = (tails[n % 10] || 0) + 1; });
  const maxTail = Math.max(...Object.values(tails));

  const gaps = nums.slice(1).map((n, i) => n - nums[i]);
  const isArithmetic = gaps.every((g) => g === gaps[0]);

  return { sum, odd, low31, high, zones, maxRun, maxTail, isArithmetic,
    span: nums[5] - nums[0] };
}

/* ── 전체 데이터 통계 ───────────────────────────────────── */
export function analyse(draws) {
  const n = draws.length;
  const freq = new Array(MAX_NUM + 1).fill(0);
  const lastSeen = new Array(MAX_NUM + 1).fill(-1);
  draws.forEach((d, i) => d.numbers.forEach((x) => { freq[x]++; lastSeen[x] = i; }));

  const observed = freq.slice(1);
  const expected = new Array(MAX_NUM).fill((n * PICK) / MAX_NUM);
  const uniformity = chiSquareTest(observed, expected);

  // 미출현 회차수(콜드 정도)
  const drought = [];
  for (let x = 1; x <= MAX_NUM; x++) {
    drought.push({ num: x, count: freq[x], gap: lastSeen[x] < 0 ? n : n - 1 - lastSeen[x] });
  }

  // 합계 / 홀수개수 / 이월수 분포
  const sums = draws.map((d) => features(d.numbers).sum);
  const oddCounts = new Array(7).fill(0);
  draws.forEach((d) => { oddCounts[features(d.numbers).odd]++; });

  let carryOver = 0;
  for (let i = 1; i < n; i++) {
    const prev = new Set([...draws[i - 1].numbers, draws[i - 1].bonus]);
    if (draws[i].numbers.some((x) => prev.has(x))) carryOver++;
  }

  return {
    n, freq, drought, uniformity, sums, oddCounts,
    carryOverRate: n > 1 ? carryOver / (n - 1) : 0,
    expectedPerNumber: (n * PICK) / MAX_NUM,
  };
}

/* ── 인기도 실증 분석 ───────────────────────────────────────
   1등 당첨자 수는 '그 조합을 몇 명이나 샀는가'의 직접 관측치다.
   판매액으로 정규화하면 조합 특성별 인기도를 실제로 측정할 수 있다. */
export function popularity(draws) {
  const usable = draws.filter((d) => d.totalSales > 0 && d.firstWinners >= 0);
  if (usable.length < 50) return null;

  const rate = (d) => (d.firstWinners / d.totalSales) * 1e11; // 판매액 1000억당 1등 당첨자수

  const groupBy = (label, classify) => {
    const buckets = new Map();
    usable.forEach((d) => {
      const k = classify(features(d.numbers));
      if (k === null) return;
      if (!buckets.has(k)) buckets.set(k, []);
      buckets.get(k).push(rate(d));
    });
    const rows = [...buckets.entries()]
      .map(([k, v]) => ({
        key: k, n: v.length,
        mean: v.reduce((a, b) => a + b, 0) / v.length, values: v,
      }))
      .sort((a, b) => String(a.key).localeCompare(String(b.key)));
    return { label, rows };
  };

  const birthday = groupBy('생일 편중 (1~31만으로 구성)', (f) =>
    f.low31 === 6 ? '전부 1~31' : '32 이상 포함');
  const consecutive = groupBy('연속수 포함', (f) => (f.maxRun >= 2 ? '연속수 있음' : '연속수 없음'));
  const sumBand = groupBy('번호 합계', (f) =>
    f.sum < 110 ? 'a. 110 미만' : f.sum <= 170 ? 'b. 110~170 (중앙)' : 'c. 171 이상');

  // 생일 편중 조합의 초과 인기도 — 회피 전략의 근거 수치
  const b = Object.fromEntries(birthday.rows.map((r) => [r.key, r]));
  let lift = null;
  if (b['전부 1~31'] && b['32 이상 포함']) {
    const t = twoSampleZ(b['전부 1~31'].values, b['32 이상 포함'].values);
    lift = {
      ratio: b['전부 1~31'].mean / b['32 이상 포함'].mean,
      p: t.p, nLow: b['전부 1~31'].n, nHigh: b['32 이상 포함'].n,
    };
  }
  return { groups: [birthday, consecutive, sumBand], lift, sampleSize: usable.length };
}

/* ── 번호 생성기 ────────────────────────────────────────── */

/**
 * 후보 규칙. 각 규칙이 "당첨 시 분할 인원"에 실제로 효과가 있는지는
 * 가정하지 않고 매번 데이터에서 직접 측정한다(아래 filterEvidence).
 */
export const FILTERS = [
  { id: 'highSum', label: '번호 합계 171 이상',
    test: (f) => f.sum >= 171,
    why: '합계가 큰 조합은 구매가 적습니다. 큰 번호를 잘 안 고르기 때문입니다.' },
  { id: 'hasConsecutive', label: '연속된 번호 한 쌍 이상 포함',
    test: (f) => f.maxRun >= 2,
    why: '연속수는 "당첨될 리 없다"고 여겨 기피되지만, 실제 출현 빈도는 정상입니다.' },
  { id: 'avoidBirthday', label: '32 이상 번호 2개 이상 포함',
    test: (f) => f.high >= 2,
    why: '생일(1~31)로만 찍는 구매자를 피합니다.' },
  { id: 'noSameTail', label: '같은 끝수 3개 이상 배제',
    test: (f) => f.maxTail < 3,
    why: '끝수 이론을 따르는 구매자와의 중복을 피합니다.' },
  { id: 'noArith', label: '등차수열 배제',
    test: (f) => !f.isArithmetic,
    why: '5·10·15·20·25·30 같은 규칙 조합은 다수가 동시에 선택합니다.' },
  { id: 'notPastWinner', label: '과거 1등 조합과 완전 일치 배제',
    test: null, // 과거 당첨 조합은 정의상 모두 "당첨"이라 효과를 측정할 수 없다
    why: '지난 당첨번호를 그대로 사는 구매자가 꾸준히 존재합니다.' },
];

/**
 * 각 규칙이 실제로 "덜 인기 있는" 조합을 고르는지 측정한다.
 * 1등 당첨자 수(판매액 정규화)가 규칙 통과 조합에서 더 낮을수록 효과가 있다.
 * lift < 1 이고 p < 0.05 면 근거 있음으로 본다.
 */
export function filterEvidence(draws) {
  const usable = draws.filter((d) => d.totalSales > 0);
  const rate = (d) => (d.firstWinners / d.totalSales) * 1e11;

  return FILTERS.map((f) => {
    if (!f.test || usable.length < 100) {
      return { ...f, measurable: false, significant: false, recommended: true };
    }
    const pass = [], fail = [];
    usable.forEach((d) => (f.test(features(d.numbers)) ? pass : fail).push(rate(d)));
    if (pass.length < 30 || fail.length < 30) {
      return { ...f, measurable: false, significant: false, recommended: true };
    }
    const mean = (v) => v.reduce((a, b) => a + b, 0) / v.length;
    const t = twoSampleZ(pass, fail);
    const lift = mean(pass) / mean(fail);
    const significant = t.p < 0.05 && lift < 1;
    return { ...f, measurable: true, lift, p: t.p, n: pass.length,
      significant, recommended: significant };
  });
}

function passes(nums, opts, pastSet) {
  const f = features(nums);
  for (const rule of FILTERS) {
    if (!opts[rule.id]) continue;
    if (rule.id === 'notPastWinner') {
      if (pastSet.has(nums.join(','))) return false;
    } else if (!rule.test(f)) {
      return false;
    }
  }
  return true;
}

/** 사용 빈도가 낮은 번호에 가중치를 주어 45개를 고르게 덮는 조합을 뽑는다. */
function weightedTicket(rng, usage, target) {
  const pool = [];
  for (let i = 1; i <= MAX_NUM; i++) {
    const w = Math.max(0.25, target - usage[i] + 1);
    pool.push([i, w]);
  }
  const picked = [];
  let totalW = pool.reduce((s, [, w]) => s + w, 0);
  for (let k = 0; k < PICK; k++) {
    let r = rng() * totalW;
    for (let i = 0; i < pool.length; i++) {
      if (!pool[i]) continue;
      r -= pool[i][1];
      if (r <= 0) {
        picked.push(pool[i][0]);
        totalW -= pool[i][1];
        pool[i] = null;
        break;
      }
    }
    if (picked.length <= k) { // 부동소수 잔차 대비
      const rest = pool.filter(Boolean);
      const c = rest[Math.floor(rng() * rest.length)];
      picked.push(c[0]); totalW -= c[1];
      pool[pool.findIndex((p) => p === c)] = null;
    }
  }
  return picked.sort((a, b) => a - b);
}

const overlap = (a, b) => a.filter((x) => b.includes(x)).length;

/**
 * 무작위 조합을 규칙에 맞게 최소한으로 고친다.
 * 규칙이 엄격할 때 거부 샘플링만 쓰면 특정 번호대에 쏠리고 느려지므로,
 * 조건을 어긴 자리만 바꿔 조합 분포를 넓게 유지한다.
 */
function repair(nums, opts, rng) {
  let t = nums.slice().sort((a, b) => a - b);
  const pick = (arr) => arr[Math.floor(rng() * arr.length)];

  // 연속수 한 쌍 만들기 — 한 자리를 이웃 번호로 교체한다
  if (opts.hasConsecutive && !t.some((n, i) => i > 0 && n === t[i - 1] + 1)) {
    const anchor = pick(t);
    const neighbours = [anchor - 1, anchor + 1]
      .filter((x) => x >= 1 && x <= 45 && !t.includes(x));
    if (neighbours.length) {
      const victim = pick(t.filter((x) => x !== anchor));
      t = t.map((x) => (x === victim ? pick(neighbours) : x)).sort((a, b) => a - b);
    }
  }

  // 합계 채우기 — 가장 작은 수를 남는 큰 수로 올린다
  if (opts.highSum) {
    let guard = 0;
    while (t.reduce((a, b) => a + b, 0) < 171 && guard++ < 24) {
      const room = [];
      for (let n = t[t.length - 1] + 1; n <= 45; n++) if (!t.includes(n)) room.push(n);
      if (!room.length) break;
      t = [...t.slice(1), pick(room)].sort((a, b) => a - b);
    }
  }
  return new Set(t).size === 6 ? t : nums;
}

/**
 * games 장의 조합을 생성한다.
 * 서로 겹치는 번호를 maxOverlap 이하로 제한해 포트폴리오를 분산시킨다.
 */
export function generate({ games, opts, pastDraws, seed, maxOverlap = 2 }) {
  const rng = makeRng(seed);
  const pastSet = new Set((pastDraws || []).map((d) => d.numbers.join(',')));
  const usage = new Array(MAX_NUM + 1).fill(0);
  const target = (games * PICK) / MAX_NUM;
  const tickets = [];
  let limit = maxOverlap;
  let stall = 0;

  while (tickets.length < games) {
    const t = repair(weightedTicket(rng, usage, target), opts, rng);
    const ok = passes(t, opts, pastSet)
      && tickets.every((prev) => overlap(prev, t) <= limit);
    if (ok) {
      tickets.push(t);
      t.forEach((x) => usage[x]++);
      stall = 0;
    } else if (++stall > 4000) {
      // 제약이 과해 더 못 뽑으면 겹침 한도만 한 칸 완화한다(규칙 자체는 유지)
      limit = Math.min(PICK, limit + 1);
      stall = 0;
    }
  }
  return { tickets, usage, maxOverlapUsed: limit };
}

/* ── 백테스트 ───────────────────────────────────────────── */

/** 티켓과 당첨번호를 비교해 등수를 반환한다(미당첨은 0). */
export function rank(ticket, draw) {
  const hit = ticket.filter((x) => draw.numbers.includes(x)).length;
  if (hit === 6) return 1;
  if (hit === 5) return ticket.includes(draw.bonus) ? 2 : 3;
  if (hit === 4) return 4;
  if (hit === 3) return 5;
  return 0;
}

const STRATEGIES = {
  random: () => (rng) => randomTicket(rng),
  hot: (hist) => {
    const f = new Array(MAX_NUM + 1).fill(0);
    hist.forEach((d) => d.numbers.forEach((x) => f[x]++));
    const top = rankNums(f).slice(0, 15);
    return (rng) => pickFrom(top, rng);
  },
  cold: (hist) => {
    const f = new Array(MAX_NUM + 1).fill(0);
    hist.forEach((d) => d.numbers.forEach((x) => f[x]++));
    const bottom = rankNums(f).slice(-15);
    return (rng) => pickFrom(bottom, rng);
  },
  exclude: (hist) => {
    // 이미지들이 쓰던 '제외수' 전략: 최근 다출 10개를 제외하고 나머지에서 추출
    const recent = hist.slice(-30);
    const f = new Array(MAX_NUM + 1).fill(0);
    recent.forEach((d) => d.numbers.forEach((x) => f[x]++));
    const keep = rankNums(f).slice(10);
    return (rng) => pickFrom(keep, rng);
  },
  portfolio: () => (rng) => {
    // 이 사이트의 전략: 인기 회피 규칙만 적용(당첨 확률에는 중립)
    const opts = { highSum: true, hasConsecutive: true, avoidBirthday: true,
      noSameTail: true, noArith: true };
    for (let i = 0; i < 300; i++) {
      const t = randomTicket(rng);
      if (passes(t, opts, new Set())) return t;
    }
    return randomTicket(rng);
  },
};

function rankNums(f) {
  return f.map((c, i) => [i, c]).slice(1)
    .sort((a, b) => b[1] - a[1]).map(([i]) => i);
}
function pickFrom(pool, rng) {
  const p = pool.slice();
  for (let i = 0; i < PICK; i++) {
    const j = i + Math.floor(rng() * (p.length - i));
    [p[i], p[j]] = [p[j], p[i]];
  }
  return p.slice(0, PICK).sort((a, b) => a - b);
}

/**
 * 각 전략을 과거 전 회차에 적용한다.
 * i 회차를 맞힐 때는 i 이전 데이터만 사용해 미래 정보 누수를 차단한다.
 */
export function backtest(draws, { ticketsPerDraw = 20, warmup = 100, seed = 7 } = {}) {
  const names = Object.keys(STRATEGIES);
  const hits = Object.fromEntries(names.map((k) => [k, []]));
  const tiers = Object.fromEntries(names.map((k) => [k, { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 }]));

  for (const name of names) {
    const rng = makeRng(seed);
    for (let i = warmup; i < draws.length; i++) {
      const build = STRATEGIES[name](draws.slice(0, i)); // 과거만 사용
      let matched = 0;
      for (let t = 0; t < ticketsPerDraw; t++) {
        const ticket = build(rng);
        matched += ticket.filter((x) => draws[i].numbers.includes(x)).length;
        const r = rank(ticket, draws[i]);
        if (r) tiers[name][r]++;
      }
      hits[name].push(matched / ticketsPerDraw);
    }
  }

  const base = hits.random;
  return names.map((name) => {
    const v = hits[name];
    const mean = v.reduce((a, b) => a + b, 0) / v.length;
    const test = name === 'random' ? { p: 1, diff: 0 } : twoSampleZ(v, base);
    const games = v.length * ticketsPerDraw;
    return {
      name, mean, diff: test.diff, p: test.p, games,
      prizeRate: Object.values(tiers[name]).reduce((a, b) => a + b, 0) / games,
      tiers: tiers[name],
    };
  });
}
