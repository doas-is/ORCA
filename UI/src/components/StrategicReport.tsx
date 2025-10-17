import { motion } from "motion/react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Download, Target, TrendingUp, Lightbulb } from "lucide-react";

interface StrategicReportProps {
  onExport: () => void;
  isDark: boolean;
}

const contentOpportunities = [
  {
    topic: "OSHA Compliance Automation",
    difficulty: "Medium",
    traffic: "2.4K/mo",
    gap: "High",
    reason: "Only 2/5 competitors cover this comprehensively",
  },
  {
    topic: "Mobile-First Safety Checklists",
    difficulty: "Low",
    traffic: "1.8K/mo",
    gap: "High",
    reason: "PlanGrid dominates but leaves room for detailed guides",
  },
  {
    topic: "Construction Budget Tracking",
    difficulty: "High",
    traffic: "5.2K/mo",
    gap: "Medium",
    reason: "Procore has strong presence, but technical depth missing",
  },
];

export function StrategicReport({ onExport, isDark }: StrategicReportProps) {
  const cardClass = isDark
    ? "bg-cyan-950/30 backdrop-blur-md border-cyan-500/20"
    : "bg-white/40 backdrop-blur-md border-blue-200/30";

  const textClass = isDark ? "text-cyan-100" : "text-blue-900";
  const mutedClass = isDark ? "text-cyan-300/60" : "text-blue-600/60";
  const buttonClass = isDark
    ? "bg-cyan-500 hover:bg-cyan-400 text-cyan-950"
    : "bg-blue-500 hover:bg-blue-600 text-white";

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -30 }}
      transition={{ duration: 0.6 }}
      className="w-full max-w-4xl mx-auto px-4 pb-20"
    >
      {/* Header */}
      <div className="mb-8 text-center">
        <h2 className={`${textClass}`}>Strategic Intelligence Report</h2>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={`border rounded-xl p-4 ${cardClass}`}
        >
          <div className="flex items-center gap-3 mb-2">
            <Target className={isDark ? "text-cyan-400" : "text-blue-500"} />
            <span className={mutedClass}>Total Opportunities</span>
          </div>
          <p className={`text-3xl ${textClass}`}>47</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className={`border rounded-xl p-4 ${cardClass}`}
        >
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className={isDark ? "text-cyan-400" : "text-blue-500"} />
            <span className={mutedClass}>Est. Monthly Traffic</span>
          </div>
          <p className={`text-3xl ${textClass}`}>24.8K</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className={`border rounded-xl p-4 ${cardClass}`}
        >
          <div className="flex items-center gap-3 mb-2">
            <Lightbulb className={isDark ? "text-cyan-400" : "text-blue-500"} />
            <span className={mutedClass}>Quick Wins</span>
          </div>
          <p className={`text-3xl ${textClass}`}>12</p>
        </motion.div>
      </div>

      {/* Top Content Opportunities */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className={`border rounded-2xl p-6 shadow-xl mb-6 ${cardClass}`}
      >
        <h3 className={`mb-4 ${textClass}`}>Top Content Opportunities</h3>
        <div className="space-y-4">
          {contentOpportunities.map((opportunity, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 + index * 0.1 }}
              className={`p-4 rounded-xl border ${
                isDark
                  ? "bg-cyan-900/20 border-cyan-500/20"
                  : "bg-white/30 border-blue-200/30"
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <h4 className={textClass}>{opportunity.topic}</h4>
                <Badge
                  variant="outline"
                  className={
                    opportunity.gap === "High"
                      ? isDark
                        ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/30"
                        : "bg-blue-500/20 text-blue-700 border-blue-500/30"
                      : isDark
                      ? "bg-cyan-700/20 text-cyan-400 border-cyan-700/30"
                      : "bg-blue-300/20 text-blue-600 border-blue-300/30"
                  }
                >
                  {opportunity.gap} Gap
                </Badge>
              </div>
              <div className="flex flex-wrap gap-3 mb-2">
                <span className={mutedClass}>
                  Difficulty: <span className={textClass}>{opportunity.difficulty}</span>
                </span>
                <span className={mutedClass}>
                  Traffic: <span className={textClass}>{opportunity.traffic}</span>
                </span>
              </div>
              <p className={mutedClass}>{opportunity.reason}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Key Insights */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
        className={`border rounded-2xl p-6 shadow-xl mb-6 ${cardClass}`}
      >
        <h3 className={`mb-4 ${textClass}`}>Key Insights</h3>
        <ul className="space-y-3">
          <li className={mutedClass}>
            💡 Your competitors publish an average of 8-12 articles/month. You should aim for 10-15 to gain momentum.
          </li>
          <li className={mutedClass}>
            🎯 Focus on "how-to" guides rather than news - these get 3x more backlinks in your niche.
          </li>
          <li className={mutedClass}>
            📱 Mobile construction topics are underserved - this is your biggest opportunity.
          </li>
          <li className={mutedClass}>
            🔗 Procore's backlink strategy focuses on industry partnerships - consider similar outreach.
          </li>
        </ul>
      </motion.div>

      {/* Export Button */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
        className="flex justify-center"
      >
        <Button onClick={onExport} className={`${buttonClass} px-8`}>
          <Download className="w-4 h-4 mr-2" />
          Export Full Report (JSON)
        </Button>
      </motion.div>
    </motion.div>
  );
}
