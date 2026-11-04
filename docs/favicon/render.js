const { chromium } = require('playwright');
const icons = require('./icons.js');
const fs = require('fs');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ deviceScaleFactor: 1 });
  // individual PNGs at each size
  for (const [k, svg] of Object.entries(icons)) {
    for (const s of [512, 192, 180, 96, 48, 32]) {
      await p.setViewportSize({ width: s, height: s });
      await p.setContent(`<html><body style="margin:0;background:transparent">${svg.replace('<svg ', `<svg width="${s}" height="${s}" `)}</body></html>`);
      await p.screenshot({ path: `${k}-${s}.png`, omitBackground: true, clip: { x: 0, y: 0, width: s, height: s } });
    }
  }
  // comparison sheet: large icon + browser tab mock + google result mock
  const tab = (k) => `<div class="tab"><img src="${k}-32.png" width="16" height="16"><span>ŚEORA | תכשיטי מואסנייט</span></div>`;
  const g = (k) => `<div class="g"><img src="${k}-48.png" width="26" height="26"><div><b>ŚEORA</b><small>https://www.seora.co.il</small></div></div>`;
  const col = (k, name) => `<div class="col"><h2>${name}</h2><img class="big" src="${k}-192.png">${tab(k)}${g(k)}</div>`;
  fs.writeFileSync('sheet.html', `<html dir="rtl"><head><meta charset="utf-8"><style>
    body{margin:0;padding:28px;background:#f4f4f2;font-family:Inter,Arial;display:flex;gap:28px}
    .col{background:#fff;border-radius:16px;padding:22px;display:flex;flex-direction:column;align-items:center;gap:18px;width:300px}
    h2{margin:0;font-size:22px;font-weight:500}.big{width:150px;height:150px}
    .tab{display:flex;align-items:center;gap:8px;background:#dee1e6;border-radius:8px 8px 0 0;padding:8px 12px;width:230px;font-size:12px;direction:ltr}
    .g{display:flex;align-items:center;gap:10px;direction:ltr;width:230px}.g div{display:flex;flex-direction:column;font-size:13px}.g small{color:#4d5156}
    .g img{border-radius:50%;background:#f1f3f4;padding:3px}
  </style></head><body>${col('A','אפשרות 1')}${col('B','אפשרות 2')}${col('C','אפשרות 3')}</body></html>`);
  await p.setViewportSize({ width: 1060, height: 460 });
  await p.goto('file://' + process.cwd() + '/sheet.html');
  await p.screenshot({ path: 'favicon-options.png', fullPage: true });
  await b.close();
})();
