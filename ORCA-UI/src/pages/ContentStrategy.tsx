import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Check, TrendingUp, Shield, Target, ExternalLink } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { apiService } from "@/services/api";
import { useAnalysis } from "@/contexts/AnalysisContext";
import { useToast } from "@/components/Toast";

const ContentStrategy = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const {
    companyData,
    competitorData,
    setCompetitorData,
    isLoading,
    setIsLoading,
    setError,
    currentAnalysisStep,
    setCurrentAnalysisStep,
  } = useAnalysis();

  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [checkmarks, setCheckmarks] = useState([false, false, false]);

  useEffect(() => {
    // If no company data, redirect to overview
    if (!companyData) {
      navigate("/");
      showToast("⚠️ Please analyze your company first", "error");
      return;
    }

    // If we don't have competitor data yet and not currently loading, start discovery
    if (!competitorData && !isLoading) {
      handleDiscoverCompetitors();
    }
  }, [companyData, competitorData]);

  // Restore progress state when returning to this page during loading
  useEffect(() => {
    if (isLoading && currentAnalysisStep === 2) {
      // Restore progress animation
      const progressInterval = setInterval(() => {
        setAnalysisProgress(prev => Math.min(prev + 1, 90));
      }, 150);

      return () => clearInterval(progressInterval);
    }
  }, [isLoading, currentAnalysisStep]);

  const handleDiscoverCompetitors = async () => {
    if (!companyData) return;

    setError(null);
    setIsLoading(true);
    setCurrentAnalysisStep(2); // Mark that we're on step 2
    setAnalysisProgress(0);
    setCheckmarks([false, false, false]);

    const progressInterval = setInterval(() => {
      setAnalysisProgress(prev => Math.min(prev + 1, 90));
    }, 150);

    setTimeout(() => setCheckmarks([true, false, false]), 600);
    setTimeout(() => setCheckmarks([true, true, false]), 1200);

    try {
      const result = await apiService.discoverCompetitors(companyData, 10);
      setCompetitorData(result);
      
      setCheckmarks([true, true, true]);
      clearInterval(progressInterval);
      setAnalysisProgress(100);
      
      setTimeout(() => {
        setIsLoading(false);
        setCurrentAnalysisStep(0); // Reset step
        showToast(`✅ Found ${result.statistics.total_found} competitors!`, "success");
      }, 500);
    } catch (err: any) {
      clearInterval(progressInterval);
      setError(err.message || 'Failed to discover competitors');
      setIsLoading(false);
      setCurrentAnalysisStep(0);
      showToast("❌ Failed to discover competitors", "error");
    }
  };

  const getTierBadge = (score: number) => {
    if (score >= 70) return { label: "🥇 DIRECT", color: "bg-red-500/20 text-red-300 border-red-500/30" };
    if (score >= 50) return { label: "🥈 STRONG", color: "bg-orange-500/20 text-orange-300 border-orange-500/30" };
    if (score >= 30) return { label: "🥉 MODERATE", color: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30" };
    return { label: "⚪ WEAK", color: "bg-gray-500/20 text-gray-300 border-gray-500/30" };
  };

  const getConfidenceBadge = (confidence: string) => {
    if (confidence === "high") return { icon: "🔥", text: "High Confidence", color: "bg-confidence-high/20 text-confidence-high" };
    return { icon: "⚡", text: "Medium Confidence", color: "bg-confidence-medium/20 text-confidence-medium" };
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="ocean-gradient min-h-screen pt-24 pb-16">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-2xl">
          <div className="glass-card rounded-2xl p-8 animate-fade-in">
            <h2 className="text-2xl font-bold text-foreground mb-6">Discovering Competitors...</h2>
            
            <div className="space-y-3 mb-6">
              {[
                "Scanning market landscape...",
                "Identifying key competitors...",
                "Analyzing market positioning..."
              ].map((text, i) => (
                <div key={i} className="flex items-center gap-3">
                  {checkmarks[i] ? (
                    <Check className="w-5 h-5 text-kelp animate-scale-in" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border-2 border-muted animate-pulse" />
                  )}
                  <span className="text-foreground">{text}</span>
                </div>
              ))}
            </div>
            
            <Progress value={analysisProgress} className="h-3" />
            
            <p className="text-sm text-foreground-secondary mt-4 text-center">
              Analyzing your competitive landscape...
            </p>

            <div className="mt-6 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
              <p className="text-sm text-yellow-200 text-center">
                ⚠️ Analysis in progress - navigation temporarily disabled
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!competitorData) {
    return null;
  }

  return (
    <div className="ocean-gradient min-h-screen pt-24 pb-16">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-6xl">
        {/* Header Section */}
        <div className="glass-card rounded-2xl p-8 mb-6 animate-fade-in-up">
          <h2 className="text-4xl font-bold text-foreground mb-3">Competitive Landscape</h2>
          <p className="text-foreground-secondary text-lg mb-6">
            Discovered {competitorData.statistics.total_found} competitors in your market
          </p>

          {/* Statistics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-card/50 rounded-xl p-4 border border-border">
              <div className="text-3xl font-bold text-primary mb-1">
                {competitorData.statistics.total_found}
              </div>
              <div className="text-sm text-foreground-secondary">Total Found</div>
            </div>
            <div className="bg-card/50 rounded-xl p-4 border border-border">
              <div className="text-3xl font-bold text-red-400 mb-1">
                {competitorData.statistics.direct || 0}
              </div>
              <div className="text-sm text-foreground-secondary">Direct</div>
            </div>
            <div className="bg-card/50 rounded-xl p-4 border border-border">
              <div className="text-3xl font-bold text-orange-400 mb-1">
                {competitorData.statistics.strong || 0}
              </div>
              <div className="text-sm text-foreground-secondary">Strong</div>
            </div>
            <div className="bg-card/50 rounded-xl p-4 border border-border">
              <div className="text-3xl font-bold text-yellow-400 mb-1">
                {competitorData.statistics.moderate || 0}
              </div>
              <div className="text-sm text-foreground-secondary">Moderate</div>
            </div>
          </div>
        </div>

        {/* Competitors List */}
        <div className="space-y-4 mb-8">
          {competitorData.competitors.slice(0, 10).map((comp: any, index) => {
            const tier = getTierBadge(comp.score || 0);
            const breakdown = comp.breakdown || {};
            
            return (
              <div
                key={comp.domain}
                className="glass-card rounded-xl p-6 hover-lift cursor-pointer transition-all duration-300"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                {/* Header Row */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-4 flex-1">
                    <span className="text-4xl font-bold text-kelp min-w-[50px]">#{index + 1}</span>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-2xl font-bold text-foreground">{comp.company?.name || comp.name}</h3>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${tier.color}`}>
                          {tier.label}
                        </span>
                      </div>
                      <a 
                        href={`https://${comp.domain}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-primary hover:text-primary/80 flex items-center gap-1 mb-3"
                      >
                        {comp.domain}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                      {comp.company?.description && (
                        <p className="text-sm text-foreground-secondary leading-relaxed">
                          {comp.company.description}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Score Badge */}
                  <div className="flex flex-col items-end gap-2">
                    <div className="bg-primary/20 rounded-lg px-4 py-2 text-center min-w-[80px]">
                      <div className="text-2xl font-bold text-primary">{comp.score?.toFixed(0) || "N/A"}</div>
                      <div className="text-xs text-foreground-secondary">Score</div>
                    </div>
                    {comp.confidence && (
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        comp.confidence === "high" 
                          ? "bg-confidence-high/20 text-confidence-high" 
                          : "bg-confidence-medium/20 text-confidence-medium"
                      }`}>
                        {comp.confidence === "high" ? "🔥 High" : "⚡ Medium"}
                      </span>
                    )}
                  </div>
                </div>

                {/* Score Breakdown */}
                {breakdown.ai_analysis && (
                  <div className="mt-4 pt-4 border-t border-border">
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                      {/* AI Analysis */}
                      <div className="bg-card/30 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <Shield className="w-4 h-4 text-primary" />
                          <span className="text-xs font-semibold text-foreground-secondary">AI Analysis</span>
                        </div>
                        <div className="text-lg font-bold text-foreground">
                          {breakdown.ai_analysis.points?.toFixed(1) || 0}
                          <span className="text-xs text-foreground-secondary ml-1">/ {breakdown.ai_analysis.max}</span>
                        </div>
                      </div>

                      {/* Keywords */}
                      <div className="bg-card/30 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <Target className="w-4 h-4 text-primary" />
                          <span className="text-xs font-semibold text-foreground-secondary">Keywords</span>
                        </div>
                        <div className="text-lg font-bold text-foreground">
                          {breakdown.keyword_overlap?.points?.toFixed(1) || 0}
                          <span className="text-xs text-foreground-secondary ml-1">/ {breakdown.keyword_overlap?.max}</span>
                        </div>
                      </div>

                      {/* Business Model */}
                      <div className="bg-card/30 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <TrendingUp className="w-4 h-4 text-primary" />
                          <span className="text-xs font-semibold text-foreground-secondary">Model</span>
                        </div>
                        <div className="text-lg font-bold text-foreground">
                          {breakdown.business_model?.points?.toFixed(1) || 0}
                          <span className="text-xs text-foreground-secondary ml-1">/ {breakdown.business_model?.max}</span>
                        </div>
                      </div>

                      {/* Social */}
                      <div className="bg-card/30 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-semibold text-foreground-secondary">Social</span>
                        </div>
                        <div className="text-lg font-bold text-foreground">
                          {breakdown.social_presence?.points?.toFixed(1) || 0}
                          <span className="text-xs text-foreground-secondary ml-1">/ {breakdown.social_presence?.max}</span>
                        </div>
                      </div>

                      {/* Content */}
                      <div className="bg-card/30 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-semibold text-foreground-secondary">Content</span>
                        </div>
                        <div className="text-lg font-bold text-foreground">
                          {breakdown.content_quality?.points?.toFixed(1) || 0}
                          <span className="text-xs text-foreground-secondary ml-1">/ {breakdown.content_quality?.max}</span>
                        </div>
                      </div>
                    </div>

                    {/* AI Reasoning */}
                    {breakdown.ai_analysis?.reasoning && (
                      <div className="mt-3 text-xs text-foreground-secondary italic bg-card/20 rounded-lg p-3">
                        💡 {breakdown.ai_analysis.reasoning}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <Button 
            variant="outline" 
            className="flex-1" 
            onClick={() => navigate("/")}
          >
            Back to Overview
          </Button>
          <Button
            onClick={() => {
              navigate("/insights");
              showToast("📊 Loading strategic insights...", "info");
            }}
            className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground"
          >
            View Insights Dashboard <ArrowRight className="ml-2" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ContentStrategy;