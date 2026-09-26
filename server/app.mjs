import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { DatabaseSync } from 'node:sqlite';
import { createLeaderboardHandler, openDatabase } from './leaderboard.mjs';

const PORT = Number(process.env.PORT || 8082);
const HOST = process.env.HOST || '0.0.0.0';
const ORIGIN = process.env.ORIGIN;
const TRUST_PROXY = process.env.TRUST_PROXY === '1';
// Only for local development: production static files are served by nginx.
const STATIC_INDEX = process.env.STATIC_INDEX;

const db = openDatabase(DatabaseSync, process.env.DB_PATH || 'skyhoy.sqlite');
const leaderboard = createLeaderboardHandler({ db, origin: ORIGIN });

const WINDOW = 60_000, LIMIT = 40;
const hits = new Map();
setInterval(() => { const cutoff = Date.now() - WINDOW; for (const [ip, h] of hits) if (h.start < cutoff) hits.delete(ip); }, WINDOW).unref();
function limited(ip) {
 const time = Date.now(), h = hits.get(ip);
 if (!h || time - h.start > WINDOW) { hits.set(ip, { start: time, count: 1 }); return false; }
 return ++h.count > LIMIT;
}

async function toRequest(req) {
 const chunks = []; let size = 0;
 for await (const chunk of req) { size += chunk.length; if (size > 4096) break; chunks.push(chunk); }
 const url = new URL(req.url, ORIGIN || `http://${req.headers.host}`);
 const init = { method: req.method, headers: req.headers };
 if (!['GET', 'HEAD'].includes(req.method)) init.body = Buffer.concat(chunks);
 return new Request(url, init);
}

const server = createServer(async (req, res) => {
 const path = new URL(req.url, 'http://x').pathname;
 const send = (status, body, type = 'application/json; charset=utf-8') => { res.writeHead(status, { 'Content-Type': type, 'Cache-Control': 'no-store' }); res.end(body); };
 try {
  if (path === '/api/health') return send(200, '{"ok":true}');
  if (path === '/api/leaderboard') {
   const ip = (TRUST_PROXY && req.headers['x-real-ip']) || req.socket.remoteAddress;
   if (limited(ip)) return send(429, '{"error":"For mange forespørsler."}');
   const response = await leaderboard(await toRequest(req));
   res.writeHead(response.status, Object.fromEntries(response.headers));
   return res.end(await response.text());
  }
  if (STATIC_INDEX && (path === '/' || path === '/index.html')) return send(200, await readFile(STATIC_INDEX), 'text/html; charset=utf-8');
  send(404, '{"error":"Ikke funnet."}');
 } catch (error) {
  console.error('Request failed:', error?.message || 'unknown');
  if (!res.headersSent) send(500, '{"error":"Serverfeil."}');
 }
});
server.listen(PORT, HOST, () => console.log(`SKYHØY leaderboard listening on ${HOST}:${PORT}`));
for (const signal of ['SIGTERM', 'SIGINT']) process.on(signal, () => server.close(() => { db.close(); process.exit(0); }));
