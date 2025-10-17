import { motion } from "motion/react";

export function UnderwaterBackground({ isActive }: { isActive: boolean }) {
  if (!isActive) return null;

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* Animated gradient background */}
      <motion.div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(180deg, #0a1929 0%, #001a2e 30%, #00101c 60%, #000810 100%)",
        }}
        animate={{
          backgroundPosition: ["0% 0%", "0% 100%"],
        }}
        transition={{
          duration: 20,
          repeat: Infinity,
          ease: "linear",
        }}
      />

      {/* Glowing orb 1 */}
      <motion.div
        className="absolute w-96 h-96 rounded-full opacity-20"
        style={{
          background:
            "radial-gradient(circle, rgba(34, 211, 238, 0.4) 0%, transparent 70%)",
          filter: "blur(60px)",
        }}
        animate={{
          x: ["-10%", "10%", "-10%"],
          y: ["20%", "60%", "20%"],
          scale: [1, 1.2, 1],
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
        className="absolute w-80 h-80 rounded-full opacity-15 right-0"
        style={{
          background:
            "radial-gradient(circle, rgba(6, 182, 212, 0.5) 0%, transparent 70%)",
          filter: "blur(70px)",
        }}
        animate={{
          x: ["10%", "-5%", "10%"],
          y: ["40%", "80%", "40%"],
          scale: [1, 1.3, 1],
        }}
        transition={{
          duration: 18,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 2,
        }}
        initial={{ x: "10%", y: "40%" }}
      />

      {/* Subtle particles/bubbles */}
      {[...Array(8)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-2 h-2 rounded-full bg-cyan-300/20"
          style={{
            left: `${(i * 15) % 100}%`,
            filter: "blur(1px)",
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
