import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {install,status,update,pythonCandidatesFor} from '../src/lifecycle.mjs';
const ROOT=fileURLToPath(new URL('..',import.meta.url));
const CLI=path.join(ROOT,'bin/commerce-ui.mjs');
const temp=()=>fs.mkdtemp(path.join(os.tmpdir(),'commerce-ui-test-'));
test('fresh, repeated and modified managed copy lifecycle',async()=>{
 const root=await temp(),r=await install(root,'copy');assert.equal(r.state,'current');
 assert.equal((await update(root)).action,'unchanged');
 await fs.appendFile(path.join(r.destination,'SKILL.md'),'\n用户内容');
 assert.equal((await status(root)).state,'modified');await assert.rejects(update(root),e=>e.code==='UNMANAGED_TARGET');
});
test('unmanaged targets and unknown modes are refused',async()=>{
 const root=await temp();await fs.mkdir(path.join(root,'compact-commerce-ui'));await assert.rejects(install(root),e=>e.code==='TARGET_EXISTS');
 await assert.rejects(install(await temp(),'invalid'),e=>e.code==='USAGE');
});
test('locked in-place update backs up and preserves customized metadata',async()=>{
 const root=await temp(),r=await install(root,'copy');
 const m=path.join(r.destination,'.commerce-ui-npm-managed.json');const v=JSON.parse(await fs.readFile(m,'utf8'));v.sourceDigest='previous';await fs.writeFile(m,JSON.stringify(v));
 await fs.writeFile(path.join(r.destination,'.install-meta.json'),'custom metadata');
 const updated=await update(root,{forceInPlace:true});assert.equal(updated.state,'current');assert.equal(updated.updateStrategy,'in-place');assert.equal(await fs.readFile(path.join(updated.destination,'.install-meta.json'),'utf8'),'custom metadata');assert.ok(await fs.stat(updated.backup));
});
test('Python candidates cover Agent-managed runtimes on both operating systems',()=>{
 for(const p of ['darwin','win32'])assert.ok(pythonCandidatesFor(p,'test-home','agent-home').some(c=>c.includes('binaries')&&c.includes('default')));
});
test('canonical Skill discovery works without Python, missing configured runtime is structured',()=>{
 const env={...process.env,COMMERCE_UI_PYTHON:'nonexistent-commerce-python'};
 const source=spawnSync(process.execPath,[CLI,'skill','source','--json'],{encoding:'utf8',env});assert.equal(source.status,0);assert.ok(JSON.parse(source.stdout).source.includes('compact-commerce-ui'));
 const r=spawnSync(process.execPath,[CLI,'doctor','--json'],{encoding:'utf8',env});assert.equal(r.status,1);assert.equal(JSON.parse(r.stderr).error.code,'RUNTIME_UNAVAILABLE');
});
test('renders non-ASCII evidence, validates and refuses to overwrite',async()=>{
 const root=await temp(),out=path.join(root,'报告.html');
 const args=['render','--input',path.join(ROOT,'runtime/tests/minimal.json'),'--output',out];
 const r=spawnSync(process.execPath,[CLI,...args],{encoding:'utf8',env:{...process.env,COMMERCE_UI_DATA_ROOT:path.join(root,'data')}});assert.equal(r.status,0,r.stderr);
 const v=spawnSync(process.execPath,[CLI,'validate',out,'--json'],{encoding:'utf8'});assert.equal(v.status,0,v.stderr);assert.ok(JSON.parse(v.stdout).ok);
 const bytes=await fs.readFile(out);assert.equal(spawnSync(process.execPath,[CLI,...args],{encoding:'utf8'}).status,1);assert.deepEqual(await fs.readFile(out),bytes);
});
