import { motion, AnimatePresence } from "motion/react";
import { useEffect, useState } from "react";

const statusMessages = [
  "extracting names",
  "extracting niches",
  "generating reports",
  "scanning websites",
  "analyzing competitors",
  "finalizing dashboard",
];

interface StatusPillProps {
  isActive: boolean;
}

export function StatusPill({ isActive }: StatusPillProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (!isActive) return;

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % statusMessages.length);
    }, 1500);

    return () => clearInterval(interval);
  }, [isActive]);

  if (!isActive) return null;

  return (
    <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50">
      <div className="bg-cyan-900/80 backdrop-blur-md border border-cyan-400/30 rounded-full px-6 py-3 shadow-lg shadow-cyan-500/20">
        <AnimatePresence mode="wait">
          <motion.p
            key={currentIndex}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="text-cyan-100 text-center min-w-[200px]"
          >
            {statusMessages[currentIndex]}
          </motion.p>
        </AnimatePresence>
      </div>
    </div>
  );
}
