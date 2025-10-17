import { motion } from "motion/react";
import { Check, Loader2 } from "lucide-react";

interface DeepDiveAnalysisProps {
  progress: number;
  isDark: boolean;
}

const crawlSteps = [
  { label: "Crawling Procore.com...", articles: 43, threshold: 0 },
  { label: "Crawling Buildertrend.com...", articles: 67, threshold: 20 },
  { label: "Crawling CoConstruct.com...", articles: 31, threshold: 40 },
  { label: "Crawling PlanGrid.com...", articles: 22, threshold: 60 },
  { label: "Crawling eSUB.com...", articles: 18, threshold: 80 },
];

const analysisSteps = [
  { label: "Identifying content gaps...", threshold: 85 },
  { label: "Scoring opportunities...", threshold: 90 },
  { label: "Generating your strategy...", threshold: 95 },
];

export function DeepDiveAnalysis({ progress, isDark }: DeepDiveAnalysisProps) {
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
          <h2 className={`${textClass}`}>Deep Dive: Analyzing Competitor Content...</h2>
        </div>

        {/* Crawling Steps */}
        <div className="space-y-3 mb-6">
          {crawlSteps.map((step, index) => {
            const isComplete = progress > step.threshold;
            const isActive = progress >= step.threshold && progress < (crawlSteps[index + 1]?.threshold || 80);
            
            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
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
                  {isComplete ? (
                    <Check className="w-4 h-4" />
                  ) : isActive ? (
                    <Loader2 className={`w-4 h-4 animate-spin ${isDark ? "text-cyan-400" : "text-blue-500"}`} />
                  ) : null}
                </div>
                <span className={isComplete || isActive ? textClass : mutedClass}>
                  {step.label}{" "}
                  {isComplete && (
                    <span className={mutedClass}>({step.articles} articles found)</span>
                  )}
                </span>
              </motion.div>
            );
          })}
        </div>

        {/* Analysis Steps */}
        <div className="space-y-3 mb-6 pt-6" style={{ borderTop: isDark ? "1px solid rgba(6, 182, 212, 0.2)" : "1px solid rgba(59, 130, 246, 0.2)" }}>
          {analysisSteps.map((step, index) => {
            const isComplete = progress > step.threshold;
            const isActive = progress >= step.threshold && progress < (analysisSteps[index + 1]?.threshold || 100);
            
            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 + index * 0.1 }}
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
                  {isComplete ? (
                    <Check className="w-4 h-4" />
                  ) : isActive ? (
                    <Loader2 className={`w-4 h-4 animate-spin ${isDark ? "text-cyan-400" : "text-blue-500"}`} />
                  ) : null}
                </div>
                <span className={isComplete || isActive ? textClass : mutedClass}>
                  {step.label}
                </span>
              </motion.div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
