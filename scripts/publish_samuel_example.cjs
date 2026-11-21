const fs = require('node:fs');
const path = require('node:path');
const {paired, cohorts, summarize} = require('../samuel/model.js');

const start = '<!-- SAMUEL-EXAMPLE:START -->';
const end = '<!-- SAMUEL-EXAMPLE:END -->';

function renderExample(data) {
  const prices = paired(data, 'spx');
  const results = cohorts(prices, {months: 6, years: 3});
  const stats = summarize(results);
  if (!stats) throw Error('No completed SPY/BIL comparisons for the Samuel example');

  const first = results[0].month, last = results.at(-1).month;
  const asOf = prices.at(-1)[0];
  const share = (count) => (count * 100 / stats.n).toFixed(1) + '%';
  const gap = (100 * stats.medianGap).toFixed(1);
  const signedGap = Number(gap) === 0 ? '0.0' : Number(gap) > 0 ? '+' + gap : gap;
  const koTies = stats.ties ? ` 동률은 ${stats.ties}회였습니다.` : '';
  const enTies = stats.ties ? ` The two tied in ${stats.ties}.` : '';

  return `<section class="historical-example" aria-labelledby="example-heading">
    <h2 id="example-heading"><span data-lang="ko">S&amp;P 500에 한 번에 넣을까, 6개월로 나눠 넣을까?</span><span data-lang="en">Invest in the S&amp;P 500 all at once or over six months?</span></h2>
    <div data-lang="ko">
      <p>${first}부터 ${last}까지 시작월을 한 달씩 옮겨 같은 목돈을 SPY에 투자했을 때의 결과를 비교했습니다. 3년 뒤 일시금 투자에 더 많이 남은 경우는 ${stats.n}개 시작월 중 <strong>${stats.lump}회(${share(stats.lump)})</strong>, 분할 투자에 더 많이 남은 경우는 ${stats.split}회(${share(stats.split)})였습니다.${koTies} 각 시작월의 3년 수익률 차이(일시금 − 분할)를 구하면 중앙값은 ${signedGap}%p였습니다.</p>
      <p class="assumptions">대기 자금은 미국 초단기 국채 ETF인 BIL에 두고 두 ETF의 분배금은 재투자했습니다. 각 시작월의 3년 구간은 서로 겹칩니다. 자료 기준일 ${asOf}.</p>
    </div>
    <div data-lang="en">
      <p>We compared two ways to invest the same cash in SPY for every starting month from ${first} through ${last}. After three years, lump-sum investing finished ahead in <strong>${stats.lump} of ${stats.n} starts (${share(stats.lump)})</strong> and phased investing in ${stats.split} (${share(stats.split)}).${enTies} The median difference in three-year total return (lump sum minus phased, paired by starting month) was ${signedGap} percentage points.</p>
      <p class="assumptions">Waiting funds were held in BIL, a U.S. Treasury bill ETF. Distributions from both ETFs were reinvested. The three-year periods overlap. Data through ${asOf}.</p>
    </div>
  </section>`;
}

function updateExample(html, data) {
  const from = html.indexOf(start), to = html.indexOf(end);
  if (from < 0 || to < from || from !== html.lastIndexOf(start) || to !== html.lastIndexOf(end))
    throw Error('Missing or duplicate Samuel example markers');
  const newline = html.includes('\r\n') ? '\r\n' : '\n';
  const block = (start + '\n  ' + renderExample(data) + '\n  ').replaceAll('\n', newline);
  return html.slice(0, from) + block + html.slice(to);
}

if (require.main === module) {
  const root = path.resolve(__dirname, '..');
  const file = path.join(root, 'samuel/index.html');
  const html = fs.readFileSync(file, 'utf8');
  const data = JSON.parse(fs.readFileSync(path.join(root, 'data/samuel/prices.json'), 'utf8'));
  const updated = updateExample(html, data);
  if (updated !== html) {
    if (process.argv.includes('--check')) throw Error('The published Samuel example is stale');
    fs.writeFileSync(file + '.tmp', updated);
    fs.renameSync(file + '.tmp', file);
  }
}

module.exports = {updateExample};
