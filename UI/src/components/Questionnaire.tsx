import { motion } from "motion/react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { RotateCcw } from "lucide-react";

interface QuestionnaireProps {
  onStart: () => void;
  onReset: () => void;
}

export function Questionnaire({ onStart, onReset }: QuestionnaireProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-xl"
    >
      <div className="bg-cyan-950/30 backdrop-blur-md border border-cyan-500/20 rounded-2xl p-8 shadow-2xl">
        <div className="space-y-6">
          {/* Question 1 */}
          <div className="space-y-2">
            <Label htmlFor="product" className="text-cyan-100">
              Primary product / service
            </Label>
            <Input
              id="product"
              type="text"
              placeholder="e.g., SaaS project management tool"
              className="bg-cyan-900/20 border-cyan-500/30 text-cyan-50 placeholder:text-cyan-400/40 focus:border-cyan-400/60 transition-colors"
            />
          </div>

          {/* Question 2 */}
          <div className="space-y-2">
            <Label htmlFor="audience" className="text-cyan-100">
              Main target audience
            </Label>
            <Input
              id="audience"
              type="text"
              placeholder="e.g., Small business owners, remote teams"
              className="bg-cyan-900/20 border-cyan-500/30 text-cyan-50 placeholder:text-cyan-400/40 focus:border-cyan-400/60 transition-colors"
            />
          </div>

          {/* Question 3 */}
          <div className="space-y-2">
            <Label htmlFor="location" className="text-cyan-100">
              Country / City
            </Label>
            <Input
              id="location"
              type="text"
              placeholder="e.g., United States, San Francisco"
              className="bg-cyan-900/20 border-cyan-500/30 text-cyan-50 placeholder:text-cyan-400/40 focus:border-cyan-400/60 transition-colors"
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-3 pt-4">
            <Button
              onClick={onStart}
              className="flex-1 bg-cyan-500 hover:bg-cyan-400 text-cyan-950 transition-all duration-300 shadow-lg shadow-cyan-500/20 hover:shadow-cyan-400/30"
            >
              Start Extraction
            </Button>
            <Button
              onClick={onReset}
              variant="outline"
              className="border-cyan-500/30 text-cyan-300 hover:bg-cyan-900/30 hover:text-cyan-100 transition-all"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset
            </Button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
