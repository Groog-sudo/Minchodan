import { useEffect, useRef } from "react";
import { Animated, Easing, Image, StyleSheet, Text, View } from "react-native";

const COLOR_BG = "#FFFFFF";
const COLOR_GILDANG_TEAL = "#38C9BE";
const COLOR_GILDANG_NAVY = "#123451";

// Tailwind animate-bounce와 동일한 리듬(1s, cubic ease-in-out 왕복)의 상하 바운스.
function useBounce(): Animated.Value {
  const bounce = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(bounce, {
          toValue: 1,
          duration: 500,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(bounce, {
          toValue: 0,
          duration: 500,
          easing: Easing.in(Easing.quad),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [bounce]);

  return bounce;
}

export function LoadingScreen() {
  const bounce = useBounce();
  const translateY = bounce.interpolate({
    inputRange: [0, 1],
    outputRange: [0, -18],
  });

  return (
    <View style={styles.container}>
      <Animated.View style={[styles.bounceGroup, { transform: [{ translateY }] }]}>
        <Image
          source={require("../../assets/brand/gildang-mascot.jpg")}
          style={styles.mascot}
          resizeMode="contain"
          accessibilityLabel="길댕 마스코트"
        />
        <Image
          source={require("../../assets/brand/gildang-wordmark.png")}
          style={styles.wordmark}
          resizeMode="contain"
          accessibilityLabel="길댕"
        />
        <Text style={styles.loadingText}>시스템을 준비하고 있습니다</Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLOR_BG,
    alignItems: "center",
    justifyContent: "center",
  },
  bounceGroup: {
    alignItems: "center",
  },
  mascot: {
    width: 260,
    height: 260,
    shadowColor: COLOR_GILDANG_NAVY,
    shadowOpacity: 0.12,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 0 },
    elevation: 8,
  },
  wordmark: {
    width: 190,
    height: 100,
    marginTop: -18,
  },
  loadingText: {
    marginTop: 4,
    color: COLOR_GILDANG_TEAL,
    fontSize: 16,
    fontWeight: "700",
    letterSpacing: 0.8,
  },
});
