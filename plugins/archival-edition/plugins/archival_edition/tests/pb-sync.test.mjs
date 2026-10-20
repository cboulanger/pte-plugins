// Tests the Autosearch fallback extension with the editor's jsdom: node --test (PTE_ROOT = editor checkout)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(process.env.PTE_ROOT ?? path.join(here, '../../../../pdf-tei-editor'));
const { JSDOM } = createRequire(path.join(root, 'package.json'))('jsdom');

const dom = new JSDOM('');
globalThis.Node = dom.window.Node;
globalThis.FrontendExtensionPlugin = class {};
const source = readFileSync(path.join(here, '../extensions/pb-sync.js'), 'utf8').replace('export default class', 'globalThis.Ext = class');
new Function(source)();
const { pageForNode } = globalThis.Ext;

const xml = readFileSync(path.join(here, '../../../examples/sample-letter.tei.xml'), 'utf8');
const doc = new dom.window.DOMParser().parseFromString(xml, 'application/xml');
const TEI = 'http://www.tei-c.org/ns/1.0';
const first = (name) => doc.getElementsByTagNameNS(TEI, name)[0];

test('content on the first photograph follows the form pages', () => {
  assert.equal(pageForNode(first('salute'), 8), 7);
});

test('content after the second <pb/> is on the second photograph', () => {
  const closer = first('closer');
  assert.equal(pageForNode(closer, 8), 8);
});

test('a page outside the PDF is rejected', () => {
  assert.equal(pageForNode(first('closer'), 7), null);
});

test('other documents are ignored', () => {
  const other = new dom.window.DOMParser().parseFromString('<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><pb/><p/></text></TEI>', 'application/xml');
  assert.equal(pageForNode(other.getElementsByTagNameNS(TEI, 'p')[0], 9), null);
});
