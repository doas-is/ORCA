import { motion } from "motion/react";
import { Check } from "lucide-react";

interface AnalyzingMarketProps {
  progress: number;
  isDark: boolean;
}

const steps = [
  { label: "Understanding your business...", threshold: 0 },
  { label: "Identifying your competitors...", threshold: 33 },
  { label: "Analyzing their content strategies...", threshold: 66 },
];

export function AnalyzingMarket({ progress, isDark }: AnalyzingMarketProps) {
  const cardClass = isDark
    ? "bg-cyan-950/30 backdrop-blur-md border-cyan-500/20"
    : "bg-white/40 backdrop-blur-md border-blue-200/30";

  const textClass = isDark ? "text-cyan-100" : "text-blue-900";
  const mutedClass = isDark ? "text-cyan-300/60" : "text-blue-600/60";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-2xl mx-auto px-4"
    >
      <div className={`border rounded-2xl p-8 shadow-2xl ${cardClass}`}>
        {/* Header */}
        <div className="mb-8 text-center">
          <h2 className={`${textClass}`}>Analyzing Your Market...</h2>
        </div>

        {/* Steps */}
        <div className="space-y-4 mb-8">
          {steps.map((step, index) => {
            const isComplete = progress > step.threshold;
            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.2 }}
                className="flex items-center gap-3"
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center transition-all duration-500 ${
                    isComplete
                      ? isDark
                        ? "bg-cyan-500 text-cyan-950"
                        : "bg-blue-500 text-white"
                      : isDark
                      ? "bg-cyan-900/30 border border-cyan-500/30"
                      : "bg-blue-100/50 border border-blue-300/40"
                  }`}
                >
                  {isComplete && <Check className="w-4 h-4" />}
                </div>
                <span className={isComplete ? textClass : mutedClass}>
                  {step.label}
                </span>
              </motion.div>
            );
          })}
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div
            className={`h-3 rounded-full overflow-hidden ${
              isDark ? "bg-cyan-900/30" : "bg-blue-100/50"
            }`}
          >
            <motion.div
              className={`h-full ${
                isDark
                  ? "bg-gradient-to-r from-cyan-500 to-cyan-400"
                  : "bg-gradient-to-r from-blue-500 to-blue-400"
              }`}
              initial={{ width: "0%" }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <div className="flex justify-between items-center mt-2">
            <span className={mutedClass}>{Math.round(progress)}%</span>
          </div>
        </div>

        {/* Status */}
        <p className={`text-center ${mutedClass}`}>
          This takes about 2 minutes...
        </p>
      </div>
    </motion.div>
  );
}
