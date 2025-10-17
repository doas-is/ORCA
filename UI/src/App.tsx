import { useState, useEffect } from "react";
import { AnimatePresence } from "motion/react";
import { OrcaLogo } from "./components/OrcaLogo";
import { ThemeToggle } from "./components/ThemeToggle";
import { AnimatedBackground } from "./components/AnimatedBackground";
import { WebsiteInput } from "./components/WebsiteInput";
import { AnalyzingMarket } from "./components/AnalyzingMarket";
import { MarketResults } from "./components/MarketResults";
import { DeepDiveAnalysis } from "./components/DeepDiveAnalysis";
import { StrategicReport } from "./components/StrategicReport";
import { Toaster } from "./components/ui/sonner";
import { toast } from "sonner@2.0.3";

type Phase = "websiteInput" | "analyzing" | "results" | "deepDive" | "report";

export default function App() {
  const [phase, setPhase] = useState<Phase>("websiteInput");
  const [progress, setProgress] = useState(0);
  const [isDark, setIsDark] = useState(true);
  const [depth, setDepth] = useState(0); // 0 = surface, 1-3 = progressively deeper

  // Load Google Fonts
  useEffect(() => {
    const link = document.createElement("link");
    link.href =
      "https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;600&display=swap";
    link.rel = "stylesheet";
    document.head.appendChild(link);
  }, []);

  // Update depth based on phase
  useEffect(() => {
    const depthMap: Record<Phase, number> = {
      websiteInput: 0,
      analyzing: 1,
      results: 1,
      deepDive: 2,
      report: 3,
    };
    setDepth(depthMap[phase]);
  }, [phase]);

  // Handle analyze website
  const handleAnalyze = (website: string, competitors: string[]) => {
    toast.success(`Analyzing ${website}...`);
    setPhase("analyzing");
    setProgress(0);

    // Simulate analysis progress
    const duration = 6000; // 6 seconds
    const interval = 50;
    const steps = duration / interval;
    const increment = 100 / steps;

    let currentProgress = 0;
    const timer = setInterval(() => {
      currentProgress += increment;
      if (currentProgress >= 100) {
        currentProgress = 100;
        clearInterval(timer);
        setTimeout(() => {
          setPhase("results");
        }, 500);
      }
      setProgress(currentProgress);
    }, interval);
  };

  // Handle continue to deep dive
  const handleContinue = () => {
    toast.success("Starting deep dive analysis...");
    setPhase("deepDive");
    setProgress(0);

    // Simulate deep dive progress
    const duration = 8000; // 8 seconds
    const interval = 50;
    const steps = duration / interval;
    const increment = 100 / steps;

    let currentProgress = 0;
    const timer = setInterval(() => {
      currentProgress += increment;
      if (currentProgress >= 100) {
        currentProgress = 100;
        clearInterval(timer);
        setTimeout(() => {
          setPhase("report");
        }, 500);
      }
      setProgress(currentProgress);
    }, interval);
  };

  // Handle export
  const handleExport = () => {
    const mockData = {
      business: {
        industry: "B2B SaaS - Construction Project Management",
        description: "Construction companies manage projects, track compliance, and coordinate teams",
        mainTopics: ["Project management", "OSHA compliance", "safety tracking", "team collaboration"],
      },
      competitors: [
        { name: "Procore.com", da: 72, confidence: "High", overlap: 85, keywords: 147, articlesPerMonth: 12 },
        { name: "Buildertrend.com", da: 68, confidence: "High", overlap: 78, keywords: 102, articlesPerMonth: 8 },
        { name: "CoConstruct.com", da: 61, confidence: "High", overlap: 72, keywords: 89, articlesPerMonth: 6 },
        { name: "PlanGrid.com", da: 65, confidence: "Medium", overlap: 68, keywords: 76, isNew: true },
        { name: "eSUB.com", da: 54, confidence: "Medium", overlap: 63 },
      ],
      contentOpportunities: [
        {
          topic: "OSHA Compliance Automation",
          difficulty: "Medium",
          monthlyTraffic: 2400,
          gap: "High",
          reason: "Only 2/5 competitors cover this comprehensively",
        },
        {
          topic: "Mobile-First Safety Checklists",
          difficulty: "Low",
          monthlyTraffic: 1800,
          gap: "High",
          reason: "PlanGrid dominates but leaves room for detailed guides",
        },
        {
          topic: "Construction Budget Tracking",
          difficulty: "High",
          monthlyTraffic: 5200,
          gap: "Medium",
          reason: "Procore has strong presence, but technical depth missing",
        },
      ],
      summary: {
        totalOpportunities: 47,
        estimatedMonthlyTraffic: 24800,
        quickWins: 12,
      },
      generatedAt: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(mockData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `orca-strategic-report-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success("Strategic report exported successfully!");
  };

  const bgClass = isDark
    ? ""
    : "bg-gradient-to-b from-sky-100 to-blue-300";

  return (
    <div
      className={`min-h-screen relative overflow-x-hidden ${bgClass}`}
      style={{
        fontFamily: "'Inter', system-ui, sans-serif",
      }}
    >
      {/* Animated background */}
      <AnimatedBackground depth={depth} isDark={isDark} />

      {/* Theme toggle */}
      <ThemeToggle isDark={isDark} onToggle={() => setIsDark(!isDark)} />

      {/* Main content */}
      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Logo - always at top */}
        <div className="py-8 flex items-center justify-center">
          <OrcaLogo isSmall={phase !== "websiteInput"} />
        </div>

        {/* Content area */}
        <div className="flex-1 flex items-start justify-center px-4 pt-8">
          <AnimatePresence mode="wait">
            {phase === "websiteInput" && (
              <WebsiteInput
                key="websiteInput"
                onAnalyze={handleAnalyze}
                isDark={isDark}
              />
            )}

            {phase === "analyzing" && (
              <AnalyzingMarket
                key="analyzing"
                progress={progress}
                isDark={isDark}
              />
            )}

            {phase === "results" && (
              <MarketResults
                key="results"
                onContinue={handleContinue}
                isDark={isDark}
              />
            )}

            {phase === "deepDive" && (
              <DeepDiveAnalysis
                key="deepDive"
                progress={progress}
                isDark={isDark}
              />
            )}

            {phase === "report" && (
              <StrategicReport
                key="report"
                onExport={handleExport}
                isDark={isDark}
              />
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Toast notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          style: isDark
            ? {
                background: "rgba(8, 51, 68, 0.9)",
                border: "1px solid rgba(34, 211, 238, 0.3)",
                color: "#a5f3fc",
                backdropFilter: "blur(10px)",
              }
            : {
                background: "rgba(255, 255, 255, 0.9)",
                border: "1px solid rgba(59, 130, 246, 0.3)",
                color: "#1e40af",
                backdropFilter: "blur(10px)",
              },
        }}
      />
    </div>
  );
}
