import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import vm from 'node:vm';

const html = await readFile(new URL('../public/index.html', import.meta.url), 'utf8');
new vm.Script(html.match(/<script>([\s\S]*?)<\/script>/)[1]);
if (!html.includes('NS = 32')) throw new Error('Wrong game edition');

if (!process.argv.includes('--check')) {
  const dist = new URL('../dist/', import.meta.url);
  await rm(dist, { recursive: true, force: true });
  await mkdir(dist);
  await writeFile(new URL('index.html', dist), html);
}
console.log('SKYHØY 32 is ready.');
