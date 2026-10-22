const pluginId = process.env.PLUGIN_ID;
const pluginPath = process.env.PLUGIN_PATH;
if (!pluginId || !pluginPath) {
  throw new Error('PLUGIN_ID and PLUGIN_PATH environment variables are required');
}

export default {
  branches: ['main'],
  tagFormat: `${pluginId}-v\${version}`,
  plugins: [
    ['./scripts/release/scoped-release-plugin.js', { preset: 'angular' }],
    [
      '@semantic-release/exec',
      {
        prepareCmd: `python3 scripts/bump_plugin_version.py ${pluginPath} \${nextRelease.version} && python3 scripts/build_index.py`,
      },
    ],
    [
      '@semantic-release/git',
      {
        assets: ['pte-plugins.json', `${pluginPath}/src/**/pte-plugin.json`],
        // No [skip ci]: it would also suppress release.yml's tag-push trigger, since GitHub's
        // skip-ci detection applies per pushed ref and the tag points at this same commit.
        // Re-triggering this workflow is instead guarded by semantic-release.yml's own
        // `if:` condition on the commit message prefix.
        message: `chore(release): ${pluginId} \${nextRelease.version}\n\n\${nextRelease.notes}`,
      },
    ],
  ],
};
