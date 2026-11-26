// Disposable native PocketMesh R11 anchor experiment. Never a runtime gate.
import assert from 'node:assert/strict';
import {generateKeyPairSync, randomBytes} from 'node:crypto';
import {mkdtempSync, mkdirSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

const [checkout, oldDigest, newDigest] = process.argv.slice(2);
assert.ok(checkout && /^[a-f0-9]{64}$/.test(oldDigest) && /^[a-f0-9]{64}$/.test(newDigest));
assert.notEqual(oldDigest, newDigest);
const native = await import(pathToFileURL(resolve(checkout, 'src/pocket-external-anchor.mjs')).href);
const root = mkdtempSync(join(tmpdir(), 'living-anchor-fixture-'));
const dir = join(root, 'authority');
mkdirSync(dir, {mode: 0o700});
const {privateKey, publicKey} = generateKeyPairSync('ed25519');
const config = {keyId:'living-fixture', key:publicKey, maxAgeMs:5000};
const local = (epoch, digest) => ({policyEpoch:epoch, witnessSha256:digest, checkpointSha256:digest});
let server, checks = 0;
try {
  native.initializeExternalAnchor(dir, oldDigest);
  server = native.createLocalAnchorServer({directory:dir, privateKey, keyId:config.keyId});
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const endpoint = 'http://127.0.0.1:'+server.address().port+'/v1/attest';
  async function fresh() {
    const nonce = randomBytes(16).toString('hex');
    const response = await fetch(endpoint+'?nonce='+nonce, {
      redirect:'error', cache:'no-store', signal:AbortSignal.timeout(3000)
    });
    assert.ok(response.ok);
    const bytes = await response.text();
    assert.ok(Buffer.byteLength(bytes) <= 4096);
    return {nonce, proof:JSON.parse(bytes)};
  }
  const verify = (pair, state, clientConfig=config) =>
    native.verifyExternalAnchorProof({...pair, clientConfig, local:state});

  const initial = await fresh();
  assert.equal(verify(initial, local(1,oldDigest)).epoch, 1); checks++;
  native.advanceExternalAnchor(dir, 2, newDigest);
  const latest = await fresh();
  assert.equal(verify(latest, local(2,newDigest)).epoch, 2); checks++;
  assert.throws(() => verify(latest, local(1,oldDigest))); checks++;
  assert.throws(() => verify(latest, local(2,oldDigest))); checks++;
  assert.throws(() => verify(latest, local(3,newDigest))); checks++;
  assert.throws(() => verify({...initial, nonce:latest.nonce}, local(1,oldDigest))); checks++;
  const rogue = generateKeyPairSync('ed25519').publicKey;
  assert.throws(() => verify(latest, local(2,newDigest), {...config,key:rogue})); checks++;
  const altered = structuredClone(latest);
  altered.proof.statement.witnessSha256 = oldDigest;
  assert.throws(() => verify(altered, local(2,oldDigest))); checks++;
  assert.throws(() => native.advanceExternalAnchor(dir, 2, oldDigest)); checks++;
  process.stdout.write(JSON.stringify({
    schema:'living-memory-native-anchor-fixture/v1', checks_passed:checks,
    synthetic:true, authority:'NONE', status:'HELD'
  })+'\n');
} finally {
  if (server) {
    server.closeAllConnections?.();
    await new Promise(resolve => server.close(resolve));
  }
  rmSync(root, {recursive:true, force:true});
}
