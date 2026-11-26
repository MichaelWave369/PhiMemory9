// Separate Node implementation of the restricted canonical dialect and selector
// round trip. This is same-author cross-runtime checking, not external proof.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';

export function canonical(value) {
  let count=0;
  function encode(x,depth=0) {
    if(++count>4096 || depth>16) throw Error('resource bound');
    if(x===null || typeof x==='boolean')return JSON.stringify(x);
    if(typeof x==='number' && Number.isSafeInteger(x))return JSON.stringify(x);
    if(typeof x==='string' && x.length<=2048 && /^[\x20-\x7e]*$/.test(x))return JSON.stringify(x);
    if(Array.isArray(x) && x.length<=256)return '['+x.map(v=>encode(v,depth+1)).join(',')+']';
    if(x && Object.getPrototypeOf(x)===Object.prototype && Object.keys(x).length<=64) {
      return '{'+Object.keys(x).sort().map(k=>encode(k,depth+1)+':'+encode(x[k],depth+1)).join(',')+'}';
    }
    throw Error('unsupported canonical value');
  }
  const out=encode(value);if(Buffer.byteLength(out)>16384)throw Error('byte bound');return out;
}

export function roundTrip(flat) {
  const {pockets,...catalog}=structuredClone(flat);
  const nest=parent=>pockets.filter(p=>p.parent_id===parent).map(p=>({pocket_id:p.pocket_id,
    project:p.project,chromosome_ids:p.chromosome_ids,children:nest(p.pocket_id)}));
  const roots=nest(null),restored=[];
  function walk(rows,parent) {
    for(const {children,...row} of rows) {
      restored.push({...row,parent_id:parent});walk(children,row.pocket_id);
    }
  }
  walk(roots,null);restored.sort((a,b)=>a.pocket_id<b.pocket_id?-1:a.pocket_id>b.pocket_id?1:0);
  const rebuilt={...catalog,pockets:restored};
  assert.equal(canonical(flat),canonical(rebuilt));return rebuilt;
}

export function strictLoad(raw) {
  const value=JSON.parse(raw);
  if(canonical(value)!==raw)throw Error('noncanonical or duplicate wire spelling');
  return value;
}

const vectors=JSON.parse(readFileSync(new URL('../tests/fixtures/living_canonical_v1.json',import.meta.url)));
let checks=0;
for(const v of vectors) {
  assert.equal(canonical(v.value),v.canonical);
  assert.equal(createHash('sha256').update(v.canonical).digest('hex'),v.sha256);checks+=2;
}
for(const invalid of [1.1,NaN,Infinity,2**53,'\u03a6','\x7f','x'.repeat(2049)]) {
  assert.throws(()=>canonical(invalid));checks++;
}
for(const invalid of ['{"a":1,"a":2}','{"a":1.0}','{"a":-0}',' {"a":1}']) {
  assert.throws(()=>strictLoad(invalid));checks++;
}
if(process.argv[2]) {
  const value=JSON.parse(readFileSync(process.argv[2],'utf8'));
  roundTrip(value);checks++;
  console.log(JSON.stringify({checks,canonical:canonical(value),
    sha256:createHash('sha256').update(canonical(value)).digest('hex'),authority:'NONE'}));
} else console.log(JSON.stringify({checks,authority:'NONE'}));
