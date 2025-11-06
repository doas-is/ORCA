import { Zap, CheckCircle2, AlertCircle, XCircle } from "lucide-react";
const QuickAudit = () => {
  return <div className="ocean-gradient min-h-screen pt-24 pb-16">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-5xl">
        <div className="text-center mb-12 animate-fade-in">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <Zap className="w-12 h-12 text-logo" />
            <h1 className="text-4xl font-bold text-foreground">ORCA</h1>
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">Quick Audit</h2>
          <p className="text-xl text-foreground-secondary">
            Fast SEO health check with actionable insights
          </p>
        </div>

        <div className="glass-card rounded-2xl p-8 mb-8 animate-fade-in">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-bold text-foreground">SEO Health Score</h3>
            <div className="text-4xl font-bold text-kelp">78/100</div>
          </div>
          <div className="h-4 bg-card/50 backdrop-blur-sm rounded-full overflow-hidden">
            <div className="h-full bg-kelp" style={{
            width: "78%"
          }} />
          </div>
        </div>

        <div className="space-y-4">
        {[{
          icon: CheckCircle2,
          label: "Mobile Optimization",
          status: "Excellent",
          color: "text-kelp",
          bg: "bg-kelp/20"
        }, {
          icon: CheckCircle2,
          label: "Page Speed",
          status: "Good",
          color: "text-primary",
          bg: "bg-primary/20"
        }, {
          icon: AlertCircle,
          label: "Meta Descriptions",
          status: "Needs Improvement",
          color: "text-confidence-medium",
          bg: "bg-confidence-medium/20"
        }, {
          icon: XCircle,
          label: "Broken Links",
          status: "Critical",
          color: "text-destructive",
          bg: "bg-destructive/20"
        }].map((item, i) => <div key={i} className="glass-card rounded-xl p-6 flex items-center justify-between animate-fade-in" style={{
          animationDelay: `${i * 100}ms`
        }}>
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-full ${item.bg} flex items-center justify-center`}>
                  <item.icon className={`w-6 h-6 ${item.color}`} />
                </div>
                <div>
                  <h4 className={`font-semibold ${item.color}`}>{item.label}</h4>
                  <p className={`text-sm ${item.color}`}>{item.status}</p>
                </div>
              </div>
              <button className="text-black dark:text-primary hover:underline text-sm">View Details →</button>
            </div>)}
        </div>
      </div>
    </div>;
};
export default QuickAudit;