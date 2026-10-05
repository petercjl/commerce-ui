#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {main,resolvePython} from '../src/lifecycle.mjs';

const root=fileURLToPath(new URL('..',import.meta.url));
const pkg=JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8'));
const args=process.argv.slice(2);
const env={...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',PYTHONDONTWRITEBYTECODE:'1'};
function run(binary,argv,options={}) {
 const r=spawnSync(binary,binary==='py'?['-3',...argv]:argv,{env,...options});
 if(r.error)throw Object.assign(r.error,{code:'RUNTIME_UNAVAILABLE'});
 return r;
}
try {
 if(args[0]==='version')console.log(args.includes('--json')?JSON.stringify({cli:'commerce-ui',package:pkg.name,version:pkg.version}):pkg.version);
 else if(args[0]==='capabilities')console.log(fs.readFileSync(path.join(root,'skill/compact-commerce-ui/capabilities.json'),'utf8'));
 else if(['skill','update'].includes(args[0]))await main(args);
 else if(args[0]==='runtime' && args[1]==='install') {
  if(!args.includes('--yes'))throw Object.assign(new Error('Pass --yes to create the managed Python environment and install declared dependencies'),{code:'CONFIRMATION_REQUIRED'});
  const dir=path.join(os.homedir(),'.local/share/commerce-ui/.venv');
  let python;
  for(const candidate of [process.env.COMMERCE_UI_PYTHON,'python3','python','py'].filter(Boolean)) {
   let r;try {r=run(candidate,['-c','import sys; assert sys.version_info >= (3,10)'],{encoding:'utf8'});}catch{continue;}
   if(r.status===0){python=candidate;break;}
  }
  if(!python)throw Object.assign(new Error('Install Python 3.10 or newer, then retry runtime install'),{code:'RUNTIME_UNAVAILABLE'});
  const target=path.join(dir,process.platform==='win32'?'Scripts/python.exe':'bin/python');
  if(!fs.existsSync(dir)) {
   const r=run(python,['-m','venv',dir],{stdio:'inherit'});if(r.status!==0)throw Object.assign(new Error('Virtual environment creation failed'),{code:'INSTALL_FAILED'});
  }
  if(!fs.existsSync(target))throw Object.assign(new Error('Existing runtime directory is not a virtual environment; inspect it before retrying'),{code:'TARGET_EXISTS'});
  const r=run(target,['-m','pip','install','-r',path.join(root,'requirements.txt')],{stdio:'inherit'});
  if(r.status!==0)throw Object.assign(new Error('Dependency installation failed'),{code:'INSTALL_FAILED'});
  console.log(JSON.stringify({ok:true,python:target,environment:dir}));
 } else {
  const python=await resolvePython();
  if(!python)throw Object.assign(new Error('Python 3.10+ with jsonschema is unavailable; run commerce-ui runtime install --yes'),{code:'RUNTIME_UNAVAILABLE'});
  const script=path.join(root,'runtime/commerce_ui.py');
  if(args[0]==='test-runtime') {
   const r=run(python,['-m','unittest','discover','-s',path.join(root,'runtime/tests'),'-p','test_*.py'],{stdio:'inherit',cwd:path.join(root,'runtime')});process.exitCode=r.status??1;
  } else {
   const forwarded=args[0]==='doctor'?args.filter(a=>a!=='--json'):args;
   const r=run(python,[script,...forwarded],{stdio:'inherit'});process.exitCode=r.status??1;
  }
 }
} catch(e) {
 console.error(JSON.stringify({ok:false,error:{code:e.code||'COMMAND_FAILED',message:e.message}}));process.exitCode=1;
}
