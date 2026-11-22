const { getDefaultConfig } = require('expo/metro-config');
const config = getDefaultConfig(__dirname);
config.transformer.babelTransformerPath = require.resolve('react-native-svg-transformer/expo');
// Disable Metro worker_threads pool to avoid V8 semi-space OOM on Windows/Node 24.
config.transformer.unstable_workerThreads = false;
config.maxWorkers = 1;
config.resolver.assetExts = config.resolver.assetExts.filter((ext) => ext !== 'svg');
config.resolver.sourceExts.push('svg');
module.exports = config;
