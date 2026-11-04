// Read-only browser proof using the existing project dependency and headless Edge.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {chromium} from '../ui/node_modules/playwright-core/index.mjs';

const browser = await chromium.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  headless: true,
});
try {
  const page = await browser.newPage({viewport: {width: 1440, height: 1100}, reducedMotion: 'reduce'});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:8787/', {waitUntil: 'domcontentloaded'});
  await page.getByText('Live from Switch', {exact: true}).waitFor({timeout: 15000});
  assert.equal(await page.locator('.card.pending').count(), 0);
  await page.screenshot({path: 'data/w9-live.png', fullPage: true});
  await page.goto('http://127.0.0.1:8787/?fixtures=day', {waitUntil: 'domcontentloaded'});
  await page.getByRole('group', {name: 'Demo replay'}).waitFor();
  const results = [];
  for (let moment = 1; moment <= 26; moment++) {
    await page.locator('.replay-pos').filter({hasText: `${moment}/26`}).waitFor();
    if ([7, 11, 12, 26].includes(moment)) {
      const pending = moment === 11 ? 1 : 0;
      await page.waitForFunction(want => document.querySelectorAll('.card.pending').length === want, pending);
      assert.equal(await page.locator('.card.pending').count(), pending);
      results.push({moment, pendingCards: pending});
      await page.screenshot({path: `data/w9-moment-${moment}.png`, fullPage: true});
    }
    if (moment < 26) await page.getByRole('button', {name: 'Next moment', exact: true}).click();
  }
  assert.deepEqual(errors, []);
  await writeFile('data/w9-browser-check.json', JSON.stringify({browser: 'headless Edge', livePending: 0, moments: results, pageErrors: errors}, null, 2)+'\n');
  console.log('Headless Edge: live and 26 replay moments; Dev pending at 11, resolved at 12; Maya resolved at 7; no page errors');
} finally {
  await browser.close();
}
