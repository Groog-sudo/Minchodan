const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Register .tflite extension as an asset to prevent runtime loading failure
config.resolver.assetExts.push('tflite');

module.exports = config;
