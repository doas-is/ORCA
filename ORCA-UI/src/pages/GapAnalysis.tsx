import { Search, Target } from "lucide-react";

const GapAnalysis = () => {
  return (
    <div className="ocean-gradient min-h-screen pt-24 pb-16">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-6xl">
        <div className="text-center mb-12 animate-fade-in">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <Search className="w-12 h-12 text-logo" />
            <h1 className="text-4xl font-bold text-foreground">ORCA</h1>
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">Gap Analysis</h2>
          <p className="text-xl text-foreground-secondary">
            Identify content and keyword gaps in your competitive landscape
          </p>
        </div>

        <div className="glass-card rounded-2xl p-8 mb-8 animate-fade-in">
          <h3 className="text-2xl font-bold text-foreground mb-6">Content Gap Matrix</h3>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-foreground font-semibold">Topic</th>
                  <th className="text-center py-3 px-4 text-foreground font-semibold">Your Site</th>
                  <th className="text-center py-3 px-4 text-foreground font-semibold">Procore</th>
                  <th className="text-center py-3 px-4 text-foreground font-semibold">Buildertrend</th>
                  <th className="text-center py-3 px-4 text-foreground font-semibold">Opportunity</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { topic: "Project Scheduling", you: "●", comp1: "●", comp2: "●", score: "Medium" },
                  { topic: "Budget Management", you: "○", comp1: "●", comp2: "●", score: "High" },
                  { topic: "Mobile Apps", you: "○", comp1: "○", comp2: "●", score: "High" },
                  { topic: "Team Collaboration", you: "●", comp1: "●", comp2: "○", score: "Low" },
                  { topic: "OSHA Compliance", you: "○", comp1: "○", comp2: "○", score: "Very High" },
                ].map((row, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-secondary/30 transition-colors">
                    <td className="py-3 px-4 text-foreground">{row.topic}</td>
                    <td className="text-center py-3 px-4">
                      <span className={row.you === "●" ? "text-kelp" : "text-foreground-secondary"}>
                        {row.you}
                      </span>
                    </td>
                    <td className="text-center py-3 px-4">
                      <span className={row.comp1 === "●" ? "text-kelp" : "text-foreground-secondary"}>
                        {row.comp1}
                      </span>
                    </td>
                    <td className="text-center py-3 px-4">
                      <span className={row.comp2 === "●" ? "text-kelp" : "text-foreground-secondary"}>
                        {row.comp2}
                      </span>
                    </td>
                    <td className="text-center py-3 px-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        row.score === "Very High" ? "bg-kelp/20 text-kelp" :
                        row.score === "High" ? "bg-kelp/20 text-kelp" :
                        row.score === "Medium" ? "bg-confidence-medium/20 text-confidence-medium" :
                        "bg-secondary text-foreground-secondary"
                      }`}>
                        {row.score}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-8 animate-fade-in-up">
          <div className="flex items-center gap-3 mb-6">
            <Target className="w-8 h-8 text-kelp" />
            <h3 className="text-2xl font-bold text-foreground">Top Priority Gaps</h3>
          </div>
          
          <div className="space-y-3">
            {[
              "OSHA Compliance content - Zero competition, high search volume",
              "Budget Management guides - Competitors dominate, but opportunity for differentiation",
              "Mobile app tutorials - Growing demand, minimal comprehensive coverage",
            ].map((gap, i) => (
              <div key={i} className="flex items-start gap-3 p-4 bg-kelp/10 rounded-lg">
                <span className="text-foreground dark:text-kelp font-bold">{i + 1}.</span>
                <p className="text-foreground">{gap}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GapAnalysis;
