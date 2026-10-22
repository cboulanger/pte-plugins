import { CommitParser } from 'conventional-commits-parser';
import angularPreset from 'conventional-changelog-angular';
import * as commitAnalyzer from '@semantic-release/commit-analyzer';
import * as releaseNotesGenerator from '@semantic-release/release-notes-generator';

// Same parserOpts @semantic-release/commit-analyzer and @semantic-release/release-notes-generator
// use internally when configured with `preset: 'angular'` (see release.config.js), so a commit
// the real analyzer can read is never invisible to this filter for reasons unrelated to scope.
const parser = new CommitParser(angularPreset().parser);

export function filterByScope(commits, pluginId) {
  return commits.filter((commit) => parser.parse(commit.message).scope === pluginId);
}

function requirePluginId() {
  const pluginId = process.env.PLUGIN_ID;
  if (!pluginId) throw new Error('PLUGIN_ID environment variable is required');
  return pluginId;
}

export async function analyzeCommits(pluginConfig, context) {
  const commits = filterByScope(context.commits, requirePluginId());
  return commitAnalyzer.analyzeCommits(pluginConfig, { ...context, commits });
}

export async function generateNotes(pluginConfig, context) {
  const commits = filterByScope(context.commits, requirePluginId());
  return releaseNotesGenerator.generateNotes(pluginConfig, { ...context, commits });
}
