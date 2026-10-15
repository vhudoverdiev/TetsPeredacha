const {chromium}=require('playwright');
(async()=>{
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Yandex.app/Contents/MacOS/Yandex'});
const page=await browser.newPage({viewport:{width:1440,height:956}});
await page.goto('http://127.0.0.1:5092/login');
await page.fill('[name=username]','e2e-admin');
await page.fill('[name=password]','E2E-visual-password-2026!');
await page.locator('.login-form').evaluate(form=>{form.dataset.csrfReady='1'});
await Promise.all([page.waitForURL(url=>!url.pathname.startsWith('/login')),page.locator('.login-submit').click()]);

await page.goto('http://127.0.0.1:5092/objects/1/edit');
for (const width of [1440,1100,440]) {
 await page.setViewportSize({width,height:956});
 const field=page.locator('#signature');
 await field.scrollIntoViewIfNeeded();
 console.log(width,await field.evaluate(el=>({width:el.getBoundingClientRect().width,form:el.form.enctype,overflow:el.getBoundingClientRect().right>innerWidth})));
 await field.locator('..').screenshot({path:'_codex_chat_files/signature-field-'+width+'.png'});
}
await browser.close();
})();
