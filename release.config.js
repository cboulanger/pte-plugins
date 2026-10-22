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
        message: `chore(release): ${pluginId} \${nextRelease.version} [skip ci]\n\n\${nextRelease.notes}`,
      },
    ],
  ],
};
