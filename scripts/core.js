/**
 * Access to a PDF-TEI-Editor checkout ("core") from plugin tests.
 *
 * Plugin tests use core's test helpers and Node dependencies (jsdom etc.). The checkout
 * is taken from the PTE_ROOT environment variable, by default `../pdf-tei-editor`
 * next to this repository.
 */

import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');

/** Absolute path of the core checkout */
export const PTE_ROOT = resolve(process.env.PTE_ROOT ?? join(repoRoot, '..', 'pdf-tei-editor'));

/**
 * Import an ES module of the core checkout.
 * @param {string} relativePath - Path relative to the checkout, e.g. `tests/api/helpers/test-auth.js`
 * @returns {Promise<any>} The module namespace
 */
export function coreImport(relativePath) {
  return import(pathToFileURL(join(PTE_ROOT, relativePath)).href);
}

/** `require` that resolves packages from core's node_modules */
export const coreRequire = createRequire(join(PTE_ROOT, 'package.json'));
