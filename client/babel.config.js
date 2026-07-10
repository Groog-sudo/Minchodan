module.exports = function (api) {
  api.cache(true);
  return {
    presets: ["babel-preset-expo"],
    // react-native-worklets-core: useFrameProcessor 내부 'worklet' 지시어를
    // 컴파일 타임에 변환한다(반사 경로 카메라 프레임 프로세서 전환, 2026-07-09).
    plugins: ["react-native-worklets-core/plugin"],
  };
};
