import { randomUUID } from 'node:crypto';

const RUN_TTL = 24 * 60 * 60 * 1000;
const headers = { 'Content-Type':'application/json; charset=utf-8', 'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff' };
const json = (body,status=200) => new Response(JSON.stringify(body),{status,headers});

export function openDatabase(DatabaseSync, path) {
 const db = new DatabaseSync(path);
 db.exec(`
  PRAGMA journal_mode = WAL;
  PRAGMA busy_timeout = 5000;
  CREATE TABLE IF NOT EXISTS runs (
   id TEXT PRIMARY KEY,
   started_at INTEGER NOT NULL,
   name TEXT,
   score INTEGER,
   world INTEGER,
   created_at TEXT
  );
  CREATE INDEX IF NOT EXISTS runs_board ON runs (score DESC, world DESC, created_at, id) WHERE name IS NOT NULL;
  CREATE INDEX IF NOT EXISTS runs_pending ON runs (started_at) WHERE name IS NULL;
 `);
 return db;
}

// Database is injected so tests run against an in-memory SQLite without production data.
export function createLeaderboardHandler({ db, origin: allowedOrigin, now=Date.now, makeId=randomUUID }) {
 const top = db.prepare('SELECT name, score, world, created_at AS createdAt FROM runs WHERE name IS NOT NULL ORDER BY score DESC, world DESC, created_at, id LIMIT 100');
 const insertRun = db.prepare('INSERT INTO runs (id, started_at) VALUES (?, ?)');
 const getRun = db.prepare('SELECT * FROM runs WHERE id = ?');
 // The first claim fixes the score for this run. Retrying the same submission is safe.
 const claim = db.prepare('UPDATE runs SET name = ?, score = ?, world = ?, created_at = ? WHERE id = ? AND name IS NULL');
 const rankOf = db.prepare(`SELECT COUNT(*) AS ahead FROM runs WHERE name IS NOT NULL AND (
  score > :score OR (score = :score AND (world > :world OR (world = :world AND (created_at < :createdAt OR (created_at = :createdAt AND id < :id))))))`);
 const prune = db.prepare('DELETE FROM runs WHERE name IS NULL AND started_at < ?');
 let lastPrune = 0;
 const scores = () => top.all().map(row => ({...row}));

 return async function handle(request) {
  try {
   if(!['GET','POST'].includes(request.method)) return json({error:'Metoden støttes ikke.'},405);
   const origin=request.headers.get('origin');
   if(origin && origin!==(allowedOrigin||new URL(request.url).origin)) return json({error:'Åpne spillet på denne nettsiden.'},403);
   if(request.method==='GET') return json({scores:scores()});
   if(!request.headers.get('content-type')?.includes('application/json')) return json({error:'Ugyldig forespørsel.'},415);
   if(Number(request.headers.get('content-length'))>2048) return json({error:'Forespørselen er for stor.'},413);
   const raw=await request.text();
   if(raw.length>2048) return json({error:'Forespørselen er for stor.'},413);
   let body;try{body=JSON.parse(raw);}catch{return json({error:'Ugyldig forespørsel.'},400);}
   if(!body || typeof body!=='object')return json({error:'Ugyldig forespørsel.'},400);
   if(body.action==='start'){
    const runId=makeId(),startedAt=now();
    insertRun.run(runId,startedAt);
    if(startedAt-lastPrune>60*60*1000){lastPrune=startedAt;prune.run(startedAt-RUN_TTL);}
    return json({runId},201);
   }
   if(body.action!=='submit')return json({error:'Ukjent handling.'},400);
   const {runId,score,world}=body;
   const name=typeof body.name==='string'?body.name.normalize('NFKC').trim().replace(/\s+/g,' '):'';
   if(!/^[0-9a-f-]{36}$/.test(runId||''))return json({error:'Start en ny runde før du sender inn.'},400);
   if(!/^[\p{L}\p{N} ._!'-]{1,20}$/u.test(name))return json({error:'Bruk 1–20 bokstaver, tall eller enkle tegn i navnet.'},400);
   if(!Number.isSafeInteger(score)||score<0||score>1_000_000_000||!Number.isInteger(world)||world<1||world>32)return json({error:'Ugyldig resultat.'},400);
   let run=getRun.get(runId);
   if(!run)return json({error:'Denne runden finnes ikke. Start en ny runde.'},400);
   if(run.name===null){
    const elapsed=now()-run.started_at;
    if(elapsed>RUN_TTL)return json({error:'Runden er utløpt. Start en ny runde.'},410);
    if(elapsed<3000 || score>1_000_000+elapsed/1000*200_000)return json({error:'Resultatet passer ikke med rundens varighet.'},400);
    claim.run(name,score,world,new Date(now()).toISOString(),runId);
    run=getRun.get(runId);
   }
   if(run.name!==name||run.score!==score||run.world!==world)return json({error:'Denne runden er allerede sendt inn med et annet resultat.'},409);
   const rank=rankOf.get({score,world,createdAt:run.created_at,id:runId}).ahead+1;
   return json({rank:rank>100?null:rank,scores:scores()});
  }catch(error){
   console.error('Leaderboard storage failed:',error?.message||'unknown');
   return json({error:'Rekordlisten er midlertidig utilgjengelig. Prøv igjen.'},503);
  }
 };
}
