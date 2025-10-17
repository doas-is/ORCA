import { motion } from "motion/react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Building2, Target, Edit3, ArrowRight } from "lucide-react";

interface MarketResultsProps {
  onContinue: () => void;
  isDark: boolean;
}

const mockCompetitors = [
  {
    name: "Procore.com",
    da: 72,
    confidence: "High Confidence (3 methods)",
    overlap: 85,
    keywords: 147,
    articles: 12,
    isNew: false,
  },
  {
    name: "Buildertrend.com",
    da: 68,
    confidence: "High Confidence (3 methods)",
    overlap: 78,
    keywords: 102,
    articles: 8,
    isNew: false,
  },
  {
    name: "CoConstruct.com",
    da: 61,
    confidence: "High Confidence (2 methods)",
    overlap: 72,
    keywords: 89,
    articles: 6,
    isNew: false,
  },
  {
    name: "PlanGrid.com",
    da: 65,
    confidence: "Medium Confidence (2 methods)",
    overlap: 68,
    keywords: 76,
    articles: null,
    isNew: true,
    specialty: "mobile construction software",
  },
  {
    name: "eSUB.com",
    da: 54,
    confidence: "Medium Confidence (2 methods)",
    overlap: 63,
    keywords: null,
    articles: null,
    isNew: false,
  },
];

export function MarketResults({ onContinue, isDark }: MarketResultsProps) {
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
        <h2 className={`${textClass}`}>Here's What We Found</h2>
      </div>

      {/* Business Analysis */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className={`border rounded-2xl p-6 shadow-xl mb-6 ${cardClass}`}
      >
        <div className="flex items-center gap-2 mb-4">
          <Building2 className={isDark ? "text-cyan-400" : "text-blue-500"} />
          <h3 className={textClass}>YOUR BUSINESS</h3>
        </div>
        <div className="space-y-3">
          <p className={textClass}>
            Based on your website, you're in:{" "}
            <span className={isDark ? "text-cyan-300" : "text-blue-600"}>
              "B2B SaaS - Construction Project Management"
            </span>
          </p>
          <p className={mutedClass}>
            You help: Construction companies manage projects, track compliance,
            and coordinate teams.
          </p>
          <p className={mutedClass}>
            <span className={textClass}>Main topics:</span> Project management,
            OSHA compliance, safety tracking, team collaboration
          </p>
          <Button
            variant="ghost"
            size="sm"
            className={isDark ? "text-cyan-400 hover:bg-cyan-900/20" : "text-blue-600 hover:bg-blue-100/50"}
          >
            <Edit3 className="w-4 h-4 mr-2" />
            Edit this if anything's wrong
          </Button>
        </div>
      </motion.div>

      {/* SEO Competitors */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className={`border rounded-2xl p-6 shadow-xl ${cardClass}`}
      >
        <div className="flex items-center gap-2 mb-4">
          <Target className={isDark ? "text-cyan-400" : "text-blue-500"} />
          <h3 className={textClass}>YOUR SEO COMPETITORS</h3>
        </div>
        <p className={`mb-6 ${mutedClass}`}>
          We analyzed Google rankings for your main topics and identified these
          competitors:
        </p>

        {/* Competitors List */}
        <div className="space-y-3 mb-6">
          {mockCompetitors.map((competitor, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 + index * 0.1 }}
              className={`p-4 rounded-xl border ${
                isDark
                  ? "bg-cyan-900/20 border-cyan-500/20 hover:border-cyan-500/40"
                  : "bg-white/30 border-blue-200/30 hover:border-blue-300/50"
              } transition-all`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={textClass}>{index + 1}. {competitor.name}</span>
                    <span className={mutedClass}>DA: {competitor.da}</span>
                  </div>
                  <div className="flex flex-wrap gap-2 mb-2">
                    <Badge
                      variant="outline"
                      className={
                        competitor.confidence.includes("High")
                          ? isDark
                            ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/30"
                            : "bg-blue-500/20 text-blue-700 border-blue-500/30"
                          : isDark
                          ? "bg-cyan-700/20 text-cyan-400 border-cyan-700/30"
                          : "bg-blue-300/20 text-blue-600 border-blue-300/30"
                      }
                    >
                      🔥 {competitor.confidence}
                    </Badge>
                    {competitor.isNew && (
                      <Badge
                        variant="outline"
                        className={isDark ? "bg-yellow-500/20 text-yellow-300 border-yellow-500/30" : "bg-yellow-500/20 text-yellow-700 border-yellow-500/30"}
                      >
                        ⭐ NEW DISCOVERY
                      </Badge>
                    )}
                  </div>
                  <p className={mutedClass}>Topic overlap: {competitor.overlap}%</p>
                  {competitor.keywords && (
                    <p className={mutedClass}>
                      ├─ Ranks for {competitor.keywords} of your target keywords
                    </p>
                  )}
                  {competitor.articles && (
                    <p className={mutedClass}>
                      └─ Publishes {competitor.articles} articles/month
                    </p>
                  )}
                  {competitor.specialty && (
                    <p className={mutedClass}>
                      └─ Strong in "{competitor.specialty}"
                    </p>
                  )}
                  {competitor.isNew && (
                    <p className={`${isDark ? "text-cyan-300" : "text-blue-600"} mt-1`}>
                      💡 You might not have known about this one!
                    </p>
                  )}
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className={isDark ? "text-cyan-400 hover:bg-cyan-900/20 mt-2" : "text-blue-600 hover:bg-blue-100/50 mt-2"}
              >
                View their strategy
              </Button>
            </motion.div>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3 justify-center pt-4">
          <Button
            variant="outline"
            className={isDark ? "border-cyan-500/30 text-cyan-300 hover:bg-cyan-900/30" : "border-blue-300/40 text-blue-600 hover:bg-blue-100/50"}
          >
            ➕ Add more competitors
          </Button>
          <Button
            variant="outline"
            className={isDark ? "border-cyan-500/30 text-cyan-300 hover:bg-cyan-900/30" : "border-blue-300/40 text-blue-600 hover:bg-blue-100/50"}
          >
            ❌ Remove any
          </Button>
          <Button onClick={onContinue} className={buttonClass}>
            ✅ Looks good - Continue to insights
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
}
