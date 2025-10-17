import { motion } from "motion/react";

interface VerticalProgressBarProps {
  progress: number;
  isActive: boolean;
}

export function VerticalProgressBar({
  progress,
  isActive,
}: VerticalProgressBarProps) {
  if (!isActive) return null;

  return (
    <div className="fixed right-6 top-1/2 -translate-y-1/2 z-50">
      <div className="flex flex-col items-center gap-3">
        {/* Progress percentage */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-cyan-300 bg-cyan-950/50 backdrop-blur-sm rounded-full px-3 py-1 border border-cyan-500/20"
        >
          {Math.round(progress)}%
        </motion.div>

        {/* Vertical bar container */}
        <div className="relative w-2 h-64 bg-cyan-950/50 rounded-full border border-cyan-500/20 overflow-hidden backdrop-blur-sm">
          {/* Progress fill */}
          <motion.div
            className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-cyan-400 via-cyan-500 to-cyan-300 rounded-full"
            initial={{ height: "0%" }}
            animate={{ height: `${progress}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />

          {/* Glow effect at the top of progress */}
          {progress > 0 && (
            <motion.div
              className="absolute left-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-cyan-300 blur-sm"
              style={{
                bottom: `${progress}%`,
                marginBottom: "-8px",
              }}
              animate={{
                opacity: [0.5, 1, 0.5],
                scale: [1, 1.2, 1],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
