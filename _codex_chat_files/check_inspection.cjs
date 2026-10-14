const {chromium}=require('playwright');
(async()=>{
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Yandex.app/Contents/MacOS/Yandex'});
const page=await browser.newPage();
await page.goto('http://127.0.0.1:5091/login');
await page.fill('[name=username]','e2e-admin');
await page.fill('[name=password]','E2E-visual-password-2026!');
await page.locator('.login-form').evaluate(form=>{form.dataset.csrfReady='1'});
await Promise.all([page.waitForURL(url=>!url.pathname.startsWith('/login')),page.locator('.login-submit').click()]);
await page.goto('http://127.0.0.1:5091/apartments/1');
console.log('PAGE',page.url(),(await page.locator('body').innerText()).slice(0,1800));
for(const date of ['2026-10-10','2026-10-11']){
await page.locator('.apartment-inspection-date-form input[type=date]').fill(date);
await Promise.all([page.waitForNavigation(),page.locator('.apartment-inspection-date-form button[type=submit]').click()]);
}
for(const width of [1440,1100,440]){
await page.setViewportSize({width,height:956});
await page.reload(); await page.waitForTimeout(600);
const row=page.locator('.apartment-compact-control-row').filter({has:page.locator('[data-apartment-inspection-display]')});
await row.scrollIntoViewIfNeeded();
console.log(width,await row.evaluate(el=>{
const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}};
return {row:rect(el),display:getComputedStyle(el.querySelector('.apartment-inspection-date-stack')).display,dates:[...el.querySelectorAll('.apartment-inspection-date-item')].map(rect),controls:rect(el.querySelector('.apartment-inline-controls'))}
}));
await row.screenshot({path:'_codex_chat_files/inspection-'+width+'.png'});
}
await browser.close();
})();
