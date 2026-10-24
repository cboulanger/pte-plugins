/**
 * Inference endpoints plugin API tests: managing endpoints and their registration as LLM providers.
 *
 * @testCovers plugins/inference-endpoints/src/pte_plugin_inference_endpoints/routes.py
 * @testCovers plugins/inference-endpoints/src/pte_plugin_inference_endpoints/plugin.py
 */
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert';
import {
  authenticatedApiCall,
  authenticatedRequest,
  loginAsAdmin,
  loginAsBasicUser,
  logout
} from '../helpers/test-auth.js';

const BASE = '/api/plugins/inference-endpoints';

/**
 * @typedef {object} EndpointResponse
 * @property {string} id
 * @property {string} provider_id
 * @property {string} name
 * @property {string} base_url
 * @property {string[]} models
 */

/**
 * @param {string} sessionId
 * @returns {Promise<Array<{id: string, models: Array<{id: string}>}>>}
 */
async function listProviders(sessionId) {
  return authenticatedApiCall(sessionId, '/llm/providers', 'GET');
}

describe('Inference endpoints plugin API', () => {
  /** @type {string} */
  let admin;
  /** @type {string} */
  let user;
  /** @type {EndpointResponse|null} */
  let endpoint = null;

  before(async () => {
    admin = (await loginAsAdmin()).sessionId;
    user = (await loginAsBasicUser()).sessionId;
  });

  after(async () => {
    if (endpoint) await authenticatedRequest(admin, `${BASE}/endpoints/${endpoint.id}`, 'DELETE');
    await logout(admin);
    await logout(user);
  });

  test('non-admins cannot list or add endpoints', async () => {
    const list = await authenticatedRequest(user, `${BASE}/endpoints`, 'GET');
    assert.strictEqual(list.status, 403);
    const add = await authenticatedRequest(user, `${BASE}/endpoints`, 'POST', { name: 'x', base_url: 'http://127.0.0.1:1/v1' });
    assert.strictEqual(add.status, 403);
  });

  test('link-local URLs are rejected', async () => {
    const response = await authenticatedRequest(admin, `${BASE}/endpoints`, 'POST', { name: 'Metadata', base_url: 'http://169.254.169.254/v1' });
    assert.strictEqual(response.status, 400);
  });

  test('an added endpoint is registered as LLM provider', async () => {
    endpoint = await authenticatedApiCall(admin, `${BASE}/endpoints`, 'POST', {
      name: 'API Test Ollama',
      base_url: 'http://127.0.0.1:1/v1',
      models: ['test-model'],
      free: true
    });
    assert.strictEqual(endpoint?.provider_id, 'endpoint-api-test-ollama');

    // free models are visible to non-admins
    const provider = (await listProviders(user)).find((p) => p.id === endpoint?.provider_id);
    assert.ok(provider, 'the provider should be listed');
    assert.deepStrictEqual(provider.models.map((m) => m.id), ['test-model']);
  });

  test('testing an unreachable endpoint reports the error', async () => {
    assert.ok(endpoint);
    const result = await authenticatedApiCall(admin, `${BASE}/endpoints/${endpoint.id}/test`, 'POST');
    assert.strictEqual(result.ok, false);
    assert.match(result.message, /Could not reach/);
  });

  test('a deleted endpoint is unregistered', async () => {
    assert.ok(endpoint);
    await authenticatedApiCall(admin, `${BASE}/endpoints/${endpoint.id}`, 'DELETE');
    const providerId = endpoint.provider_id;
    endpoint = null;
    const providers = await listProviders(admin);
    assert.ok(!providers.some((p) => p.id === providerId), 'the provider should be gone');
  });

  test('the management page is served to admins only', async () => {
    const page = await authenticatedRequest(admin, `${BASE}/manage`, 'GET');
    assert.strictEqual(page.status, 200);
    assert.match(await page.text(), /Inference Endpoints/);
    const denied = await authenticatedRequest(user, `${BASE}/manage`, 'GET');
    assert.strictEqual(denied.status, 403);
  });
});
