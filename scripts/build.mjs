import { copyFile, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import vm from 'node:vm';

const html = await readFile(new URL('../public/index.html', import.meta.url), 'utf8');
new vm.Script(html.match(/<script>([\s\S]*?)<\/script>/)[1]);
if (!html.includes('NS = 32')) throw new Error('Wrong game edition');

const dist = new URL('../dist/', import.meta.url);
await rm(dist, { recursive: true, force: true });
await mkdir(new URL('server/', dist), { recursive: true });
await writeFile(new URL('index.html', dist), html);
// Joachim i 3D, lastes bare når noen velger et 3D-kamera. Lages av scripts/joachim.blend.py i Blender.
await copyFile(new URL('../public/joachim.glb', import.meta.url), new URL('joachim.glb', dist));
// nginx denies /server/; the leaderboard container runs these from a read-only mount.
for (const file of ['app.mjs', 'leaderboard.mjs']) await copyFile(new URL('../server/' + file, import.meta.url), new URL('server/' + file, dist));
console.log('SKYHØY 32 is ready.');
