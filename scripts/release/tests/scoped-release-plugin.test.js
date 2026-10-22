import { test } from 'node:test';
import assert from 'node:assert/strict';
import { filterByScope } from '../scoped-release-plugin.js';

test('keeps only commits whose scope matches the plugin id', () => {
  const commits = [
    { message: 'fix(archival-edition): handle broken pb sync' },
    { message: 'feat(grobid): add retry' },
  ];
  assert.deepEqual(filterByScope(commits, 'archival-edition'), [commits[0]]);
});

test('drops unscoped commits', () => {
  const commits = [{ message: 'chore: update deps' }];
  assert.deepEqual(filterByScope(commits, 'archival-edition'), []);
});

test('does not match on scope substrings', () => {
  const commits = [
    { message: 'fix(grobid-extra): tweak' },
    { message: 'fix(grobid): tweak' },
  ];
  assert.deepEqual(filterByScope(commits, 'grobid'), [commits[1]]);
});

test('returns an empty array when nothing matches', () => {
  assert.deepEqual(filterByScope([{ message: 'fix(other): x' }], 'archival-edition'), []);
});
