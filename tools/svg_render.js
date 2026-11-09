// rendu d'un SVG en PNG RGBA (fond transparent) avec Chromium / Playwright (rsvg-convert absent de certaines machines)
// usage : node tools/svg_render.js in.svg out.png largeur hauteur
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [, , inp, out, w, h] = process.argv;
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 });
  const svg = fs.readFileSync(inp, 'utf8');
  await p.setContent(`<html><body style="margin:0;background:transparent"><img id=i style="width:${w}px;height:${h}px;display:block" src="data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}"></body></html>`);
  await p.waitForFunction(() => document.getElementById('i').complete);
  await p.screenshot({ path: out, omitBackground: true, clip: { x: 0, y: 0, width: +w, height: +h } });
  await b.close();
})();
