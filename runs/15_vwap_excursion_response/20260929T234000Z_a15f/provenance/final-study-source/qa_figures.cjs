// Static SVG raster inspection, not browser automation.
const fs=require('fs'),sharp=require('sharp');
const root=process.argv[2];if(!root)throw Error('Usage: node qa_figures.cjs OUTPUT_DIRECTORY');
(async()=>{
fs.mkdirSync(root+'/qa',{recursive:true});
for(const s of ['asia','london','ny','globex']){
 const files=fs.readdirSync(root+'/figures').filter(x=>x.startsWith(s+'-')||x.startsWith('example-'+s+'-')).sort();
 const thumbs=[];
 for(let i=0;i<files.length;i++)thumbs.push({input:await sharp(fs.readFileSync(root+'/figures/'+files[i])).resize(460,240).png().toBuffer(),left:(i%3)*460,top:Math.floor(i/3)*240});
 await sharp({create:{width:1380,height:Math.ceil(files.length/3)*240,channels:3,background:'#fff'}}).composite(thumbs).png().toFile(root+'/qa/'+s+'-figures.png');
 console.log(s,files.length,'SVG figures rendered');
}
for(const name of ['ny-NQ-return','ny-NQ-mae-mfe-distribution','example-asia-GC-ambiguity','example-globex-ES-through'])await sharp(fs.readFileSync(root+'/figures/'+name+'.svg')).png().toFile(root+'/qa/'+name+'.png');
})().catch(e=>{console.error(e);process.exit(1)});
