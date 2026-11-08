"""Focused offline source-link mismatch and ordered-image rendering fixture."""
import gzip, hashlib, importlib.util, json, struct, sys, tempfile, zlib
from html.parser import HTMLParser
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path('/Users/pruthvi/Documents/projects/abacus')
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
capture = load('mismatch_capture_fixture', 'studies/27_verniman_method_knowledge/capture_daily_maps.py')
builder = load('mismatch_builder_fixture', 'studies/27_verniman_method_knowledge/build_daily_maps.py')
full = 'https://1.bp.blogspot.com/example/s1600/first.png'
inline_a = 'https://1.bp.blogspot.com/example/s400/first.png'
inline_b = 'https://1.bp.blogspot.com/example/s400/second.png'
raw = ('<h3 class="post-title">Different charts</h3><div class="post-body entry-content"><p>Outlook 10/05</p><a href="' + full + '"><img src="' + inline_a + '"></a><p>Second chart follows.</p><a href="' + full + '"><img src="' + inline_b + '"></a></div>').encode()
parsed = capture.Post(raw.decode())
assert len(parsed.images) == 2 and 'source_link_qualification' not in parsed.images[0]
assert parsed.images[1]['source_link_qualification']
def png(rgb):
    def chunk(kind, data): return struct.pack('>I',len(data)) + kind + data + struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB',1,1,8,2,0,0,0)) + chunk(b'IDAT',zlib.compress(b'\x00'+bytes(rgb))) + chunk(b'IEND',b'')
with tempfile.TemporaryDirectory(prefix='daily-map-2020-image-link-') as tmp:
    stage=Path(tmp); (stage/'captures').mkdir(); (stage/'assets').mkdir()
    obj=object.__new__(capture.Capture); obj.saved_images={}; obj.image_sources={}; calls=[]
    values={full:png((255,0,0)), inline_b:png((0,0,255))}
    def fetch(url, kind):
        calls.append(url); value=values[url]; sha=hashlib.sha256(value).hexdigest(); path='assets/'+sha+'.png'; (stage/path).write_bytes(value)
        return {'url':url,'path':path,'sha256':sha,'bytes':len(value),'content_type':'image/png','capture_kind':'live'}, value
    obj.fetch=fetch
    records=[obj.image(im) for im in parsed.images]
    assert calls == [full, inline_b], calls
    assert records[0]['rendition']=='linked_full_image' and records[0]['url']==full
    assert records[1]['requested_url']==full and records[1]['url']==inline_b and records[1]['rendition']=='inline_thumbnail'
    assert records[1]['source_link_qualification'] and records[1]['full_size_error']
    assert records[0]['sha256'] != records[1]['sha256']
    compressed=gzip.compress(raw,mtime=0); path='captures/post.html.gz'; (stage/path).write_bytes(compressed)
    post={'url':'https://verniman.blogspot.com/2003/10/fixture.html','session_date':'2020-10-05','title':'Different charts','capture_kind':'live','date_method':'explicit_fixture_date','html':{'path':path,'bytes':len(compressed),'sha256':hashlib.sha256(compressed).hexdigest(),'uncompressed_sha256':hashlib.sha256(raw).hexdigest()},'images':records}
    (stage/'capture-manifest.json').write_text(json.dumps({'run_id':'fixture2020image','seed_url':post['url'],'start_date':'2020-10-05','end_date':'2020-10-05','posts':[post]}))
    result=builder.build(stage); assert result['status']=='passed'
    doc=(stage/'archive/2020/10/05/index.html').read_text()
    class Images(HTMLParser):
        def __init__(self): super().__init__(); self.sources=[]
        def handle_starttag(self,tag,attrs):
            if tag=='img': self.sources.append(dict(attrs)['src'])
    image_parser=Images(); image_parser.feed(doc)
    assert len(image_parser.sources)==2 and image_parser.sources[0]!=image_parser.sources[1]
    assert [Path(url).name for url in image_parser.sources] == [Path(record['path']).name for record in records]
    assert 'Inline rendition retained; source link points to a different image.' in doc
    assert 'href="' + inline_b + '">Source</a>' in doc
    metrics=json.loads((stage/'archive/metrics.json').read_text()); assert metrics['image_references']==2 and metrics['unique_image_files']==2 and metrics['inline_rendition_references']==1
print(json.dumps({'status':'passed','matching_filename':'linked full image preferred','mismatch':'actual inline source fetched; no guessed replacement URL','fetch_calls':2,'ordered_images_rendered':2,'distinct_image_assets':2,'qualified_inline_renditions':1}))
