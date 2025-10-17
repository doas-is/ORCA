import { motion } from "motion/react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { ArrowRight, Plus, X } from "lucide-react";
import { useState } from "react";

interface WebsiteInputProps {
  onAnalyze: (website: string, competitors: string[]) => void;
  isDark: boolean;
}

export function WebsiteInput({ onAnalyze, isDark }: WebsiteInputProps) {
  const [website, setWebsite] = useState("");
  const [competitors, setCompetitors] = useState<string[]>([]);
  const [newCompetitor, setNewCompetitor] = useState("");

  const handleAddCompetitor = () => {
    if (newCompetitor.trim()) {
      setCompetitors([...competitors, newCompetitor.trim()]);
      setNewCompetitor("");
    }
  };

  const handleRemoveCompetitor = (index: number) => {
    setCompetitors(competitors.filter((_, i) => i !== index));
  };

  const handleAnalyze = () => {
    if (website.trim()) {
      onAnalyze(website.trim(), competitors);
    }
  };

  const cardClass = isDark
    ? "bg-cyan-950/30 backdrop-blur-md border-cyan-500/20"
    : "bg-white/40 backdrop-blur-md border-blue-200/30";

  const textClass = isDark ? "text-cyan-100" : "text-blue-900";
  const mutedClass = isDark ? "text-cyan-300/60" : "text-blue-600/60";
  const inputClass = isDark
    ? "bg-cyan-900/20 border-cyan-500/30 text-cyan-50 placeholder:text-cyan-400/40"
    : "bg-white/50 border-blue-300/40 text-blue-900 placeholder:text-blue-400/50";
  const buttonClass = isDark
    ? "bg-cyan-500 hover:bg-cyan-400 text-cyan-950"
    : "bg-blue-500 hover:bg-blue-600 text-white";

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -30 }}
      transition={{ duration: 0.6 }}
      className="w-full max-w-2xl mx-auto px-4"
    >
      <div className={`border rounded-2xl p-8 shadow-2xl ${cardClass}`}>
        {/* Header */}
        <div className="mb-6">
          <h2 className={`mb-2 ${textClass}`}>Step 1: Enter Your Website</h2>
        </div>

        {/* Website Input */}
        <div className="space-y-2 mb-6">
          <Input
            type="url"
            placeholder="https://example.com"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            className={`h-12 ${inputClass}`}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAnalyze();
            }}
          />
        </div>

        {/* Analyze Button */}
        <div className="mb-8">
          <Button
            onClick={handleAnalyze}
            disabled={!website.trim()}
            className={`w-full h-12 ${buttonClass} transition-all duration-300`}
          >
            Analyze Market
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>

        {/* Optional Competitors Section */}
        <div className="pt-6 border-t" style={{ borderColor: isDark ? "rgba(6, 182, 212, 0.2)" : "rgba(59, 130, 246, 0.2)" }}>
          <p className={`mb-4 ${mutedClass}`}>
            Optional: Know your competitors? Add them here
          </p>

          {/* Competitor List */}
          {competitors.length > 0 && (
            <div className="space-y-2 mb-4">
              {competitors.map((competitor, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    isDark
                      ? "bg-cyan-900/20 border-cyan-500/20"
                      : "bg-blue-50/50 border-blue-200/30"
                  }`}
                >
                  <span className={`${textClass}`}>{competitor}</span>
                  <button
                    onClick={() => handleRemoveCompetitor(index)}
                    className={`p-1 rounded hover:bg-opacity-20 ${
                      isDark
                        ? "hover:bg-cyan-400 text-cyan-400"
                        : "hover:bg-blue-400 text-blue-600"
                    }`}
                  >
                    <X className="w-4 h-4" />
                  </button>
                </motion.div>
              ))}
            </div>
          )}

          {/* Add Competitor Input */}
          <div className="flex gap-2">
            <Input
              type="url"
              placeholder="Competitor URL"
              value={newCompetitor}
              onChange={(e) => setNewCompetitor(e.target.value)}
              className={`flex-1 ${inputClass}`}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleAddCompetitor();
              }}
            />
            <Button
              onClick={handleAddCompetitor}
              variant="outline"
              className={`${
                isDark
                  ? "border-cyan-500/30 text-cyan-300 hover:bg-cyan-900/30"
                  : "border-blue-300/40 text-blue-600 hover:bg-blue-100/50"
              }`}
            >
              <Plus className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
