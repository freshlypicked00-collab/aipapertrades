// Render logo SVGs to PNG with the pre-installed Chromium: node ops/logo_render.js in.svg out.png [size] [circle]
// "circle" also writes a preview cropped to a circle (how X, Instagram, YouTube, Telegram and Discord show a profile picture).
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [inp, out, size = '1024', circle] = process.argv.slice(2);
  const svg = fs.readFileSync(inp, 'utf8'); const s = +size;
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: s, height: s } });
  await p.setContent(`<html><body style="margin:0;background:#202020">${circle ? `<div style="width:${s}px;height:${s}px;border-radius:50%;overflow:hidden">` : '<div>'}<img src="data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}" style="width:${s}px;height:${s}px;display:block"></div></body></html>`);
  await p.waitForTimeout(150);
  await p.screenshot({ path: out, omitBackground: false, clip: { x: 0, y: 0, width: s, height: s } });
  await b.close();
})();
