import { motion } from "motion/react";
import { useEffect, useState } from "react";

interface AnimatedBackgroundProps {
  depth: number; // 0 = surface, 1 = shallow, 2 = medium, 3 = deep
  isDark: boolean;
}

export function AnimatedBackground({ depth, isDark }: AnimatedBackgroundProps) {
  const [gradientPosition, setGradientPosition] = useState(0);

  useEffect(() => {
    // Animate gradient position based on depth
    setGradientPosition(depth * 33.33); // Each depth level moves gradient up by 33.33%
  }, [depth]);

  // Dark theme gradients (underwater)
  const darkGradients = {
    0: "linear-gradient(180deg, #3b82f6 0%, #1e40af 40%, #0c1d47 70%, #050b1f 100%)", // Surface - bright blue
    1: "linear-gradient(180deg, #1e40af 0%, #0c1d47 40%, #050b1f 70%, #020610 100%)", // Shallow
    2: "linear-gradient(180deg, #0c1d47 0%, #050b1f 40%, #020610 70%, #000408 100%)", // Medium
    3: "linear-gradient(180deg, #050b1f 0%, #020610 40%, #000408 70%, #000000 100%)", // Deep
  };

  // Light theme gradients (ocean sky)
  const lightGradients = {
    0: "linear-gradient(180deg, #e0f2fe 0%, #bae6fd 40%, #7dd3fc 70%, #38bdf8 100%)", // Surface - sky blue
    1: "linear-gradient(180deg, #bae6fd 0%, #7dd3fc 40%, #38bdf8 70%, #0ea5e9 100%)", // Shallow
    2: "linear-gradient(180deg, #7dd3fc 0%, #38bdf8 40%, #0ea5e9 70%, #0284c7 100%)", // Medium
    3: "linear-gradient(180deg, #38bdf8 0%, #0ea5e9 40%, #0284c7 70%, #0369a1 100%)", // Deep
  };

  const gradients = isDark ? darkGradients : lightGradients;
  const currentGradient = gradients[depth as keyof typeof gradients] || gradients[0];

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* Main gradient background */}
      <motion.div
        className="absolute inset-0"
        style={{ background: currentGradient }}
        animate={{ backgroundPosition: `0% ${gradientPosition}%` }}
        transition={{ duration: 1.2, ease: "easeInOut" }}
      />

      {/* Glowing orb 1 */}
      <motion.div
        className="absolute w-96 h-96 rounded-full"
        style={{
          background: isDark
            ? "radial-gradient(circle, rgba(34, 211, 238, 0.3) 0%, transparent 70%)"
            : "radial-gradient(circle, rgba(59, 130, 246, 0.4) 0%, transparent 70%)",
          filter: "blur(60px)",
        }}
        animate={{
          x: ["-10%", "10%", "-10%"],
          y: ["20%", "60%", "20%"],
          scale: [1, 1.2, 1],
          opacity: isDark ? [0.2, 0.3, 0.2] : [0.3, 0.5, 0.3],
        }}
        transition={{
          duration: 15,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        initial={{ x: "-10%", y: "20%" }}
      />

      {/* Glowing orb 2 */}
      <motion.div
        className="absolute w-80 h-80 rounded-full right-0"
        style={{
          background: isDark
            ? "radial-gradient(circle, rgba(6, 182, 212, 0.4) 0%, transparent 70%)"
            : "radial-gradient(circle, rgba(96, 165, 250, 0.5) 0%, transparent 70%)",
          filter: "blur(70px)",
        }}
        animate={{
          x: ["10%", "-5%", "10%"],
          y: ["40%", "80%", "40%"],
          scale: [1, 1.3, 1],
          opacity: isDark ? [0.15, 0.25, 0.15] : [0.3, 0.5, 0.3],
        }}
        transition={{
          duration: 18,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 2,
        }}
        initial={{ x: "10%", y: "40%" }}
      />

      {/* Bubbles */}
      {[...Array(8)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-2 h-2 rounded-full"
          style={{
            left: `${(i * 15) % 100}%`,
            filter: "blur(1px)",
            background: isDark
              ? "rgba(103, 232, 249, 0.3)"
              : "rgba(59, 130, 246, 0.5)",
          }}
          animate={{
            y: ["100vh", "-10vh"],
            opacity: [0, 0.6, 0],
          }}
          transition={{
            duration: 12 + i * 2,
            repeat: Infinity,
            ease: "linear",
            delay: i * 1.5,
          }}
          initial={{ y: "100vh" }}
        />
      ))}
    </div>
  );
}
