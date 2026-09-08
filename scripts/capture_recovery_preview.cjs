'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {spawn, execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const routes = ['/', '/setup-games/', '/trabalho-estudo/', '/creator-streaming/',
  '/casa-inteligente/', '/guias/', '/comparativos/', '/recomendados/',
  '/guia/melhor-webcam-para-stream.html', '/guia/melhor-headset-gamer-custo-beneficio.html',
  '/guia/setup-gamer-custo-beneficio.html', '/review/B087CT8PWY.html'];
const output = path.resolve(process.env.CORTEX_QA_OUTPUT || '/tmp/cortex-preview-qa');
const base = 'http://127.0.0.1:8765';
const report = {sha: execFileSync('git', ['rev-parse', 'HEAD'], {encoding:'utf8'}).trim(),
  status:'RUNNING', release_approved:false, coverage:'12 selected routes; not a full-corpus visual review',
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
    for (const viewport of [{name:'mobile',width:390,height:844}, {name:'desktop',width:1440,height:900}]) {
      const page = await browser.newPage({viewport:{width:viewport.width,height:viewport.height}});
      for (const [index,route] of routes.entries()) {
        const record = {route,viewport:viewport.name,errors:[]};
        const onPageError = error => record.errors.push(error.message);
        page.on('pageerror', onPageError);
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
          Object.assign(record, await page.evaluate(() => ({
            title:document.title,
            overflow:document.documentElement.scrollWidth > innerWidth+2,
            brokenImages:[...document.images].filter(img=>!img.complete || !img.naturalWidth)
              .map(img=>({src:img.getAttribute('src'),alt:img.alt})),
            imageCount:document.images.length
          })));
          record.screenshot=`${viewport.name}-${String(index).padStart(2,'0')}.png`;
          await page.screenshot({path:path.join(output,record.screenshot),fullPage:true,timeout:20000});
        } catch(error) {record.errors.push(error.message);}
        finally {page.off('pageerror',onPageError);}
        record.status = record.errors.length || record.overflow || record.brokenImages?.length ? 'REVISE':'CAPTURED_AWAITING_VISUAL_REVIEW';
        report.pages.push(record);
        console.log(JSON.stringify(record));
      }
      await page.close();
    }
    report.status=report.pages.some(p=>p.status==='REVISE')?'REVISE':'CAPTURED_AWAITING_VISUAL_REVIEW';
  } catch(error) {report.errors.push(error.message); report.status='FAILED';}
  finally {
    fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');
    if (browser) await browser.close();
    server.kill();
  }
  if (report.errors.length || report.status==='REVISE') process.exitCode=1;
})();
