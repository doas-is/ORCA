import { Sun, Moon } from "lucide-react";
import { motion } from "motion/react";

interface ThemeToggleProps {
  isDark: boolean;
  onToggle: () => void;
}

export function ThemeToggle({ isDark, onToggle }: ThemeToggleProps) {
  return (
    <motion.button
      onClick={onToggle}
      className={`fixed top-6 right-6 z-50 p-3 rounded-full backdrop-blur-md border transition-all duration-300 ${
        isDark
          ? "bg-cyan-950/30 border-cyan-500/20 hover:border-cyan-400/40 text-cyan-300"
          : "bg-white/30 border-blue-200/40 hover:border-blue-300/60 text-blue-600"
      }`}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      <motion.div
        initial={false}
        animate={{ rotate: isDark ? 0 : 180 }}
        transition={{ duration: 0.3 }}
      >
        {isDark ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
      </motion.div>
    </motion.button>
  );
}
