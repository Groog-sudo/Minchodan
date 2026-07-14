import { useEffect, useRef } from "react";
import { Animated, Easing, Image, StyleSheet, Text, View } from "react-native";

// 콘솔(console/src/styles.css)의 "Tactical" 다크 테마를 앱 로딩 화면에도 맞춘다.
const COLOR_BG = "#0A0D10";
const COLOR_GILDANG_YELLOW = "#F9B700";

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
          source={require("../../assets/gildang-logo.jpeg")}
          style={styles.logo}
        />
        <Text style={styles.loadingText}>Loading</Text>
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
  logo: {
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 2,
    borderColor: COLOR_GILDANG_YELLOW,
    shadowColor: COLOR_GILDANG_YELLOW,
    shadowOpacity: 0.5,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 0 },
    elevation: 12,
  },
  loadingText: {
    marginTop: 20,
    color: COLOR_GILDANG_YELLOW,
    fontSize: 20,
    fontWeight: "700",
    letterSpacing: 2,
    textTransform: "uppercase",
  },
});
