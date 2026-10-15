const {chromium}=require('playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Yandex.app/Contents/MacOS/Yandex'});
 const page=await browser.newPage();
 const src=fs.readFileSync('app/static/script.js','utf8');
 const start=src.indexOf("  document.querySelectorAll('.crm-search-btn')");
 const code=src.slice(start,src.indexOf('  let activeInlineEditor',start));
 for(const zoom of [0.65,0.85,1]){
 await page.setContent('<div style="zoom:'+zoom+'"><button class="crm-search-btn" style="box-sizing:border-box;width:160px;height:48px">Найти</button></div>');
 await page.evaluate(code);
 const before=await page.locator('button').boundingBox();
 for(let i=0;i<3;i++)await page.locator('button').dispatchEvent('pointerdown');
 const after=await page.locator('button').boundingBox();
 if(Math.abs(before.width-after.width)>1||Math.abs(before.height-after.height)>1)throw Error('size changed');
 console.log(zoom,before.width,after.width);
 }
 await browser.close();
})();
