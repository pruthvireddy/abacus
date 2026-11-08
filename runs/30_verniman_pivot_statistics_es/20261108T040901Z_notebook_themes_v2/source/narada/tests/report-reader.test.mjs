import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import test from 'node:test';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import ts from 'typescript';
const require=createRequire(import.meta.url);
function compile(relativePath){
  const source=readFileSync(new URL(relativePath,import.meta.url),'utf8');
  const {outputText}=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,esModuleInterop:true}});
  const compiled={exports:{}};
  new Function('require','module','exports',outputText)(require,compiled,compiled.exports);
  return compiled.exports;
}
const {ReportContents}=compile('../src/components/report-contents.tsx');
const {SectionLink}=compile('../src/components/section-link.tsx');
const render=(Component,props)=>renderToStaticMarkup(React.createElement(Component,props));
test('desktop contents and closed mobile disclosure preserve ordinary section/evidence links without report payloads',()=>{
  const html=render(ReportContents,{sections:[{id:'question',title:'Saved question',body:'PRIVATE_BODY_SENTINEL'},{id:'outcomes',title:'Negative & unknown outcomes'}],downloads:true,references:true,notes:true});
  for(const id of ['section-question','section-outcomes','publication-downloads','publication-references','publication-notes','publication-record'])assert.equal((html.match(new RegExp(`href="#${id}"`,'g'))??[]).length,2);
  assert.match(html,/<details class="contents-mobile"><summary>/);
  assert.match(html,/aria-label="Publication contents"/);assert.match(html,/aria-label="Mobile publication contents"/);
  assert(html.includes('Negative &amp; unknown outcomes'));
  assert.match(html,/Copy section link/);assert.match(html,/disabled=""/);
  assert(!html.includes('PRIVATE_BODY_SENTINEL'));assert(!html.includes('role="tab"'));assert(!html.includes('aria-current'));
});
test('section headings retain native direct links without per-heading client controls',()=>{
  const html=render(SectionLink,{reportId:'saved-report',sectionId:'zero-null',title:'Zero & unavailable'});
  assert.match(html,/href="#section-zero-null"/);
  assert.match(html,/aria-label="Direct section link"/);
  assert(!html.includes('<button'));assert(!html.includes('script'));
});
