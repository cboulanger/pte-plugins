/**
 * Standalone integration test runner for the webdav-sync plugin.
 *
 * Starts both a FastAPI server (with WebDAV config) and a WebDAV test server,
 * runs sync.test.js, then cleans up both servers.
 *
 * Usage:
 *   WEBDAV_BASE_URL=http://localhost:8081 node plugins/webdav-sync/src/pte_plugin_webdav_sync/tests/integration/run-integration-tests.js
 *
 * The editor checkout is taken from PTE_ROOT (see scripts/core.js); the plugin must be installed into its environment.
 *
 * Environment variables (read from .env.test or process env):
 *   WEBDAV_BASE_URL     - WebDAV server base URL (required)
 *   WEBDAV_USERNAME     - WebDAV username (default: admin)
 *   WEBDAV_PASSWORD     - WebDAV password (default: admin)
 *   WEBDAV_REMOTE_ROOT  - Remote root path (default: /dav)
 */

import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { run } from 'node:test';
import { spec } from 'node:test/reporters';
import { pipeline } from 'node:stream/promises';
import { PTE_ROOT, coreImport, coreRequire } from '../../../../../../scripts/core.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = PTE_ROOT;

// Load .env.test if it exists
try {
  const { config } = coreRequire('dotenv');
  const envFile = join(projectRoot, '.env.test');
  config({ path: envFile, override: false });
} catch (e) {
  // dotenv not required
}

const { LocalServerManager } = await coreImport('tests/lib/local-server-manager.js');
const { WebdavServerManager } = await import('./webdav-server-manager.js');

const serverManager = new LocalServerManager({
  dbDir: 'tests/api/runtime/db',
  dataRoot: 'tests/api/runtime',
  logDir: 'log',
});
let webdavManager = null;
let exitCode = 0;

// Prevent SIGTERM (e.g. propagated from server shutdown) from killing the
// process before the finally block can run cleanup and call process.exit().
process.on('SIGTERM', () => process.exit(exitCode));

try {
  // Start WebDAV server
  webdavManager = new WebdavServerManager();
  await webdavManager.start({ verbose: false });
  const webdavConfig = webdavManager.getConfig();

  // Start FastAPI server with WebDAV config injected
  const baseUrl = await serverManager.start({
    cleanDb: true,
    verbose: false,
    env: {
      WEBDAV_ENABLED: webdavConfig.WEBDAV_ENABLED,
      WEBDAV_BASE_URL: webdavConfig.WEBDAV_BASE_URL,
      WEBDAV_USERNAME: webdavConfig.WEBDAV_USERNAME,
      WEBDAV_PASSWORD: webdavConfig.WEBDAV_PASSWORD,
      WEBDAV_REMOTE_ROOT: webdavConfig.WEBDAV_REMOTE_ROOT,
    },
  });

  process.env.E2E_BASE_URL = baseUrl;

  // Run tests
  const testFile = join(__dirname, 'sync.test.js');
  const stream = run({ files: [testFile] }).compose(spec);
  await pipeline(stream, process.stdout);

} catch (err) {
  console.error('Integration test run failed:', err);
  exitCode = 1;
} finally {
  if (webdavManager) {
    await webdavManager.stop({ keepRunning: false }).catch(console.error);
  }
  await serverManager.stop({ keepRunning: false }).catch(console.error);
  process.exit(exitCode);
}
