import { motion } from "motion/react";
import { Button } from "./ui/button";
import { Download, TrendingUp, Users, Award } from "lucide-react";

interface DashboardProps {
  onExport: () => void;
}

const mockCompetitors = [
  { name: "Asana", score: 92 },
  { name: "Monday.com", score: 88 },
  { name: "ClickUp", score: 85 },
];

export function Dashboard({ onExport }: DashboardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="w-full max-w-4xl"
    >
      <div className="space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Total Competitors */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-cyan-950/30 backdrop-blur-md border border-cyan-500/20 rounded-2xl p-6 shadow-xl"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 bg-cyan-500/20 rounded-xl">
                <Users className="w-6 h-6 text-cyan-300" />
              </div>
              <div>
                <p className="text-cyan-400/70">Total Competitors</p>
                <p className="text-cyan-100 mt-1">12</p>
              </div>
            </div>
          </motion.div>

          {/* Average Score */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-cyan-950/30 backdrop-blur-md border border-cyan-500/20 rounded-2xl p-6 shadow-xl"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 bg-cyan-500/20 rounded-xl">
                <TrendingUp className="w-6 h-6 text-cyan-300" />
              </div>
              <div>
                <p className="text-cyan-400/70">Average Score</p>
                <p className="text-cyan-100 mt-1">78.6</p>
              </div>
            </div>
          </motion.div>

          {/* Market Position */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-cyan-950/30 backdrop-blur-md border border-cyan-500/20 rounded-2xl p-6 shadow-xl"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 bg-cyan-500/20 rounded-xl">
                <Award className="w-6 h-6 text-cyan-300" />
              </div>
              <div>
                <p className="text-cyan-400/70">Market Position</p>
                <p className="text-cyan-100 mt-1">Strong</p>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Top Competitors */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="bg-cyan-950/30 backdrop-blur-md border border-cyan-500/20 rounded-2xl p-6 shadow-xl"
        >
          <h3 className="text-cyan-100 mb-4">Top Competitors</h3>
          <div className="space-y-3">
            {mockCompetitors.map((competitor, index) => (
              <motion.div
                key={competitor.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.7 + index * 0.1 }}
                className="flex items-center justify-between bg-cyan-900/20 rounded-xl p-4 border border-cyan-500/10 hover:border-cyan-500/30 transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-cyan-500/20 flex items-center justify-center text-cyan-300">
                    {index + 1}
                  </div>
                  <span className="text-cyan-100">{competitor.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-2 bg-cyan-900/40 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-cyan-400 to-cyan-500"
                      initial={{ width: 0 }}
                      animate={{ width: `${competitor.score}%` }}
                      transition={{ delay: 0.8 + index * 0.1, duration: 0.8 }}
                    />
                  </div>
                  <span className="text-cyan-300 min-w-[3rem] text-right">
                    {competitor.score}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Export Button */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="flex justify-center pt-4"
        >
          <Button
            onClick={onExport}
            className="bg-cyan-500 hover:bg-cyan-400 text-cyan-950 transition-all duration-300 shadow-lg shadow-cyan-500/20 hover:shadow-cyan-400/30 px-8"
          >
            <Download className="w-4 h-4 mr-2" />
            Export Results (JSON)
          </Button>
        </motion.div>
      </div>
    </motion.div>
  );
}
