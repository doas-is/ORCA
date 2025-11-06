import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Lightbulb, Target, TrendingUp, Zap, Award, BarChart3, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAnalysis } from "@/contexts/AnalysisContext";
import { useToast } from "@/components/Toast";

const Insights = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { companyData, competitorData, reset } = useAnalysis();

  useEffect(() => {
    if (!competitorData) {
      navigate("/content-strategy");
      showToast("⚠️ Please complete competitor analysis first", "error");
    }
  }, [competitorData, navigate, showToast]);

  const handleStartNewAnalysis = () => {
    reset();
    navigate("/");
    showToast("🔄 Ready for new analysis!", "info");
  };

  // Safe return with loading state
  if (!competitorData) {
    return (
      <div className="ocean-gradient min-h-screen pt-24 pb-16 flex items-center justify-center">
        <div className="glass-card rounded-2xl p-8">
          <p className="text-foreground-secondary">Loading insights...</p>
        </div>
      </div>
    );
  }

  // Get statistics with safe defaults
  const stats = competitorData.statistics || {};
  const totalFound = stats.total_found || 0;
  const directCompetitors = stats.direct || 0;
  const strongCompetitors = stats.strong || 0;
  const moderateCompetitors = stats.moderate || 0;
  const avgScore = stats.average_score || 0;
  const aiRejections = stats.ai_rejections || 0;

  // Calculate market saturation level
  const getMarketSaturation = () => {
    if (directCompetitors >= 5) return { level: "High", color: "text-red-400", description: "Highly competitive market" };
    if (directCompetitors >= 3) return { level: "Medium", color: "text-yellow-400", description: "Moderately competitive" };
    return { level: "Low", color: "text-green-400", description: "Emerging market opportunity" };
  };

  const saturation = getMarketSaturation();

  return (
    <div className="ocean-gradient min-h-screen pt-24 pb-16">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-6xl">
        
        {/* Header */}
        <div className="glass-card rounded-2xl p-10 text-center mb-8 animate-fade-in">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <Lightbulb className="w-12 h-12 text-primary" />
            <h1 className="text-4xl font-bold text-foreground">ORCA Intelligence</h1>
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Strategic Insights Dashboard</h2>
          <p className="text-xl text-foreground-secondary">
            Analysis of {totalFound} competitors for {companyData?.company?.name || "your company"}
          </p>
        </div>

        {/* Primary Metrics Grid */}
        <div className="grid gap-6 md:grid-cols-4 mb-8">
          {[
            {
              icon: Target,
              label: "Total Found",
              value: totalFound.toString(),
              description: "Competitors discovered",
              color: "text-primary",
              bgColor: "bg-primary/20"
            },
            {
              icon: Award,
              label: "Direct Rivals",
              value: directCompetitors.toString(),
              description: "High-threat competitors",
              color: "text-red-400",
              bgColor: "bg-red-500/20"
            },
            {
              icon: TrendingUp,
              label: "Strong Match",
              value: strongCompetitors.toString(),
              description: "Close competitors",
              color: "text-orange-400",
              bgColor: "bg-orange-500/20"
            },
            {
              icon: BarChart3,
              label: "Avg Score",
              value: avgScore.toFixed(1),
              description: "Competition strength",
              color: "text-primary",
              bgColor: "bg-primary/20"
            }
          ].map((metric, i) => (
            <div 
              key={i} 
              className="glass-card rounded-xl p-6 hover-lift animate-fade-in"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 rounded-full ${metric.bgColor} flex items-center justify-center`}>
                  <metric.icon className={`w-6 h-6 ${metric.color}`} strokeWidth={2.5} />
                </div>
              </div>
              <div className="text-4xl font-bold text-foreground mb-2">{metric.value}</div>
              <h3 className="text-lg font-semibold text-foreground mb-1">{metric.label}</h3>
              <p className="text-sm text-foreground-secondary">{metric.description}</p>
            </div>
          ))}
        </div>

        {/* Market Analysis */}
        <div className="grid gap-6 md:grid-cols-2 mb-8">
          {/* Market Saturation */}
          <div className="glass-card rounded-xl p-6 animate-fade-in-up">
            <div className="flex items-center gap-3 mb-4">
              <Users className="w-6 h-6 text-primary" />
              <h3 className="text-xl font-bold text-foreground">Market Saturation</h3>
            </div>
            <div className="flex items-baseline gap-3 mb-2">
              <span className={`text-4xl font-bold ${saturation.color}`}>{saturation.level}</span>
              <span className="text-foreground-secondary">{saturation.description}</span>
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-foreground-secondary">Direct competitors:</span>
                <span className="font-semibold text-foreground">{directCompetitors}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-foreground-secondary">Total market players:</span>
                <span className="font-semibold text-foreground">{totalFound}</span>
              </div>
            </div>
          </div>

          {/* AI Analysis Stats */}
          <div className="glass-card rounded-xl p-6 animate-fade-in-up" style={{ animationDelay: "100ms" }}>
            <div className="flex items-center gap-3 mb-4">
              <Zap className="w-6 h-6 text-primary" />
              <h3 className="text-xl font-bold text-foreground">AI Analysis</h3>
            </div>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-foreground-secondary">Accepted competitors</span>
                  <span className="font-semibold text-green-400">{totalFound}</span>
                </div>
                <div className="h-2 bg-card rounded-full overflow-hidden">
                  <div className="h-full bg-green-500" style={{ width: `${(totalFound / (totalFound + aiRejections)) * 100}%` }}></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-foreground-secondary">AI rejections</span>
                  <span className="font-semibold text-red-400">{aiRejections}</span>
                </div>
                <div className="h-2 bg-card rounded-full overflow-hidden">
                  <div className="h-full bg-red-500" style={{ width: `${(aiRejections / (totalFound + aiRejections)) * 100}%` }}></div>
                </div>
              </div>
              <p className="text-xs text-foreground-secondary mt-3">
                AI filtered {aiRejections} false positives with intelligent analysis
              </p>
            </div>
          </div>
        </div>

        {/* Key Insights */}
        <div className="glass-card rounded-2xl p-8 mb-8 animate-fade-in-up">
          <div className="flex items-center gap-3 mb-6">
            <Lightbulb className="w-8 h-8 text-primary" />
            <h3 className="text-2xl font-bold text-foreground">Strategic Recommendations</h3>
          </div>
          
          <div className="space-y-4">
            {[
              {
                icon: Target,
                title: "Market Positioning Strategy",
                description: directCompetitors >= 5 
                  ? `With ${directCompetitors} direct competitors, differentiation is critical. Focus on unique value propositions and specialized features that competitors lack.`
                  : `${directCompetitors} direct competitors indicates a ${directCompetitors >= 3 ? 'competitive but not saturated' : 'emerging'} market. Opportunity to establish strong positioning early.`,
              },
              {
                icon: TrendingUp,
                title: "Competitive Intelligence",
                description: `Average competitor score of ${avgScore.toFixed(1)}/100 indicates ${avgScore >= 60 ? 'strong' : avgScore >= 40 ? 'moderate' : 'weak'} competitive intensity. ${strongCompetitors + directCompetitors} close competitors require continuous monitoring.`,
              },
              {
                icon: Zap,
                title: "Growth & Opportunity Analysis",
                description: moderateCompetitors > 0 
                  ? `${moderateCompetitors} moderate competitors show adjacent market opportunities. Consider expanding into their niches or defending against their encroachment.`
                  : "Focus on defending against direct competitors while exploring untapped market segments.",
              },
              {
                icon: Users,
                title: "Market Entry Insights",
                description: saturation.level === "High"
                  ? "High market saturation requires aggressive differentiation and innovation to capture market share."
                  : saturation.level === "Medium"
                  ? "Balanced competition allows for strategic positioning. Focus on customer experience and unique features."
                  : "Low saturation presents first-mover advantages. Establish brand authority and capture market share quickly.",
              },
            ].map((insight, i) => (
              <div
                key={i}
                className="glass-card rounded-xl p-6 flex gap-4 hover-lift"
                style={{ animationDelay: `${i * 100}ms` }}
              >
                <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                  <insight.icon className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <h4 className="font-bold text-foreground mb-2">{insight.title}</h4>
                  <p className="text-foreground-secondary">{insight.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="glass-card rounded-2xl p-12 text-center animate-fade-in-up">
          <Lightbulb className="w-16 h-16 text-primary mx-auto mb-6" />
          <h2 className="text-3xl font-bold text-foreground mb-4">Analysis Complete</h2>
          <p className="text-xl text-foreground-secondary mb-8">
            Export your report or start a fresh competitive analysis
          </p>
          <div className="flex gap-4 justify-center">
            <Button
              variant="outline"
              size="lg"
              onClick={() => navigate("/content-strategy")}
              className="px-8"
            >
              View Competitors
            </Button>
            <Button
              onClick={handleStartNewAnalysis}
              size="lg"
              className="bg-primary hover:bg-primary/90 text-primary-foreground px-8"
            >
              Start New Analysis
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Insights;