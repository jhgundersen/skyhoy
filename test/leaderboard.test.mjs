import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createLeaderboardHandler,openDatabase} from '../server/leaderboard.mjs';

function setup(){
 let time=1_800_000_000_000;
 const db=openDatabase(DatabaseSync,':memory:');
 const handler=createLeaderboardHandler({db,origin:'https://skyhoy.example',now:()=>time});
 const call=async body=>{
  const response=await handler(new Request('https://skyhoy.example/api/leaderboard',body?{method:'POST',headers:{'Content-Type':'application/json','Origin':'https://skyhoy.example'},body:JSON.stringify(body)}:{}));
  return {status:response.status,...await response.json()};
 };
 return {db,handler,call,advance:(ms=10000)=>time+=ms};
}
test('empty list, server-issued round, sorted scores, one submission per round',async()=>{
 const s=setup();assert.deepEqual((await s.call()).scores,[]);
 const first=await s.call({action:'start'}),second=await s.call({action:'start'});s.advance();
 const a={action:'submit',runId:first.runId,name:'Joachim',score:40000,world:2};
 assert.equal((await s.call(a)).rank,1);
 assert.equal((await s.call({...a,runId:second.runId,name:'Ærlig spiller',score:80000,world:4})).rank,1);
 assert.equal((await s.call(a)).rank,2); // Safe retry without a duplicate.
 assert.equal((await s.call({...a,score:99999})).status,409);
 const list=await s.call();assert.equal(list.scores.length,2);assert.equal(list.scores[0].name,'Ærlig spiller');assert(!('id' in list.scores[0]));
});
test('concurrent score submissions are preserved',async()=>{
 const s=setup();const runs=await Promise.all(Array.from({length:8},()=>s.call({action:'start'})));s.advance();
 const results=await Promise.all(runs.map((run,i)=>s.call({action:'submit',runId:run.runId,name:'Spiller '+i,score:1000+i,world:1})));
 assert(results.every(r=>r.status===200));assert.equal((await s.call()).scores.length,8);
});
test('validation, malformed bodies, expiration, origin and replay rejection',async()=>{
 const s=setup(),run=await s.call({action:'start'}),base={action:'submit',runId:run.runId,name:'Test',score:50000,world:1};
 assert.equal((await s.call(base)).status,400);s.advance();
 for(const patch of [{score:-1},{score:1.5},{score:1e20},{world:33},{name:'<script>'},{name:'x'.repeat(21)},{runId:'bad'}])assert.equal((await s.call({...base,...patch})).status,400);
 const wrongOrigin=await s.handler(new Request('https://skyhoy.example/api/leaderboard',{headers:{origin:'https://other.example'}}));assert.equal(wrongOrigin.status,403);
 const invalid=await s.handler(new Request('https://skyhoy.example/api/leaderboard',{method:'POST',headers:{'Content-Type':'application/json'},body:'{'}));assert.equal(invalid.status,400);
 s.advance(24*60*60*1000);assert.equal((await s.call(base)).status,410);
});
test('top 100 stays bounded and sorted, lower ranks report null',async()=>{
 const s=setup();let last;
 for(let i=0;i<105;i++){let run=await s.call({action:'start'});s.advance();last=await s.call({action:'submit',runId:run.runId,name:'Spiller '+i,score:104-i,world:1});}
 assert.equal(last.rank,null);
 const list=await s.call();assert.equal(list.scores.length,100);assert.equal(list.scores[0].score,104);assert.equal(list.scores.at(-1).score,5);
});
test('unsubmitted runs older than a day are pruned',async()=>{
 const s=setup();await s.call({action:'start'});s.advance(25*60*60*1000);await s.call({action:'start'});
 assert.equal(s.db.prepare('SELECT COUNT(*) AS n FROM runs').get().n,1);
});
