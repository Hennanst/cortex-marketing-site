'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {spawn, execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const {loadPublicationRoutes} = require('./publication_routes.cjs');
const routes = loadPublicationRoutes();
const viewports = [{name:'mobile',width:390,height:844}, {name:'desktop',width:1440,height:900}];
const output = path.resolve(process.env.CORTEX_QA_OUTPUT || '/tmp/cortex-preview-qa');
const base = 'http://127.0.0.1:8765';
const report = {sha: execFileSync('git', ['rev-parse', 'HEAD'], {encoding:'utf8'}).trim(),
  status:'RUNNING', release_approved:false,
  coverage:`All ${routes.length} public routes from data/publication-manifest.json at ${viewports.length} viewports`,
  manifest:{path:'data/publication-manifest.json',html:routes.length,viewports:viewports.length,
    expectedCaptures:routes.length*viewports.length},
  pages:[], errors:[]};
(async () => {
  fs.mkdirSync(output, {recursive:true});
  const server = spawn('python3', ['-m','http.server','8765','--bind','127.0.0.1','--directory','dist'], {stdio:'ignore'});
  server.on('error', error => report.errors.push(`server: ${error.message}`));
  let browser;
  try {
    let ready = false;
    for (let i=0; i<30; i++) {
      try { if ((await fetch(base)).ok) {ready=true; break;} } catch {}
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!ready) throw new Error('Preview server did not become ready');
    browser = await chromium.launch();
    for (const viewport of viewports) {
      const page = await browser.newPage({viewport:{width:viewport.width,height:viewport.height}});
      for (const [index,route] of routes.entries()) {
        const record = {route,viewport:viewport.name,errors:[],consoleErrors:[]};
        const onPageError = error => record.errors.push(error.message);
        const onConsole = message => {
          if (message.type()==='error') record.consoleErrors.push(message.text());
        };
        page.on('pageerror', onPageError);
        page.on('console', onConsole);
        try {
          const response = await page.goto(base+route,{waitUntil:'domcontentloaded',timeout:30000});
          if (!response?.ok()) record.errors.push(`HTTP ${response?.status()}`);
          await page.evaluate(async () => {
            for (const img of document.images) img.loading='eager';
            await Promise.race([
              Promise.all([...document.images].map(img => img.decode().catch(()=>{}))),
              new Promise(resolve=>setTimeout(resolve,8000))
            ]);
            await Promise.race([document.fonts.ready, new Promise(resolve=>setTimeout(resolve,2000))]);
          });
          Object.assign(record, await page.evaluate(() => {
            const overflowElements=[...document.body.querySelectorAll('*')].flatMap(el=>{
              const style=getComputedStyle(el);
              const rect=el.getBoundingClientRect();
              if (style.display==='none' || style.visibility==='hidden' || rect.width===0 || rect.height===0) return [];
              if (rect.left >= -2 && rect.right <= innerWidth+2) return [];
              return [{element:`${el.tagName.toLowerCase()}${el.id?'#'+el.id:''}${[...el.classList].slice(0,2).map(c=>'.'+c).join('')}`,
                left:Math.round(rect.left),right:Math.round(rect.right),width:Math.round(rect.width)}];
            }).slice(0,20);
            return {
              title:document.title,
              viewportWidth:innerWidth,
              documentWidth:document.documentElement.scrollWidth,
              overflow:document.documentElement.scrollWidth > innerWidth+2 || overflowElements.length>0,
              overflowElements,
              brokenImages:[...document.images].filter(img=>!img.complete || !img.naturalWidth)
                .map(img=>({src:img.getAttribute('src'),alt:img.alt})),
              imageCount:document.images.length
            };
          }));
          record.screenshot=`${viewport.name}-${String(index).padStart(2,'0')}.png`;
          await page.screenshot({path:path.join(output,record.screenshot),fullPage:true,timeout:20000});
        } catch(error) {record.errors.push(error.message);}
        finally {page.off('pageerror',onPageError); page.off('console',onConsole);}
        record.status = record.errors.length || record.consoleErrors.length || record.overflow || record.brokenImages?.length
          ? 'REVISE':'CAPTURED_AWAITING_VISUAL_REVIEW';
        report.pages.push(record);
        console.log(JSON.stringify(record));
      }
      await page.close();
    }
    const observed = new Set(report.pages.map(page => `${page.viewport}:${page.route}`));
    if (report.pages.length !== report.manifest.expectedCaptures || observed.size !== report.manifest.expectedCaptures) {
      report.errors.push(`Manifest coverage mismatch: expected ${report.manifest.expectedCaptures}, observed ${observed.size}`);
    }
    report.status=report.errors.length ? 'FAILED'
      : report.pages.some(p=>p.status==='REVISE') ? 'REVISE' : 'CAPTURED_AWAITING_VISUAL_REVIEW';
  } catch(error) {report.errors.push(error.message); report.status='FAILED';}
  finally {
    fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');
    if (browser) await browser.close();
    server.kill();
  }
  if (report.errors.length || report.status==='REVISE') process.exitCode=1;
})();
