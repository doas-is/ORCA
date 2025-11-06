import { useState } from "react";
import { TrendingUp, TrendingDown, Minus, MessageCircle, ThumbsUp, ThumbsDown } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

const SentimentAnalysis = () => {
  const [brand, setBrand] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showResults, setShowResults] = useState(false);

  const [analysisProgress, setAnalysisProgress] = useState(0);

  const handleAnalyze = () => {
    if (brand.trim()) {
      setIsAnalyzing(true);
      setAnalysisProgress(0);
      
      const progressInterval = setInterval(() => {
        setAnalysisProgress((prev) => {
          if (prev >= 95) {
            clearInterval(progressInterval);
            return 95;
          }
          return prev + 2;
        });
      }, 30);

      setTimeout(() => {
        clearInterval(progressInterval);
        setAnalysisProgress(100);
        setTimeout(() => {
          setIsAnalyzing(false);
          setShowResults(true);
        }, 300);
      }, 2000);
    }
  };

  return (
    <div className="ocean-gradient min-h-screen pt-24 pb-16">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-5xl">
        <div className="text-center mb-12 animate-fade-in">
          <h1 className="text-4xl font-bold text-foreground mb-4">Sentiment Analysis</h1>
          <p className="text-xl text-foreground-secondary">
            Analyze customer sentiment across your brand and competitors
          </p>
        </div>

        <div className="glass-card rounded-2xl p-8 mb-8 animate-fade-in">
          <h3 className="text-xl font-bold text-foreground mb-4">Enter Brand or Keywords</h3>
          <div className="flex gap-3">
            <Input
              type="text"
              placeholder="e.g., Your Brand Name"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleAnalyze()}
              className="flex-1 h-12"
            />
            <Button 
              onClick={handleAnalyze}
              disabled={isAnalyzing || !brand.trim()}
              className="bg-primary hover:bg-primary/90 text-primary-foreground h-12 px-8"
            >
              {isAnalyzing ? "Analyzing..." : "Analyze Sentiment"}
            </Button>
          </div>
          {isAnalyzing && (
            <div className="mt-4">
              <Progress value={analysisProgress} className="h-2" />
              <p className="text-sm text-foreground-secondary mt-2">Analyzing sentiment across social media and reviews...</p>
            </div>
          )}
        </div>

{showResults && (
          <>
            <div className="grid gap-6 md:grid-cols-3 mb-8">
              {[
                { icon: TrendingUp, label: "Positive", value: "72%", color: "text-primary", bgColor: "bg-primary/20" },
                { icon: Minus, label: "Neutral", value: "18%", color: "text-foreground", bgColor: "bg-secondary" },
                { icon: TrendingDown, label: "Negative", value: "10%", color: "text-foreground dark:text-destructive", bgColor: "bg-destructive/20" },
              ].map((metric, i) => (
                <div
                  key={i}
                  className="glass-card rounded-xl p-6 animate-fade-in"
                  style={{ animationDelay: `${i * 100}ms` }}
                >
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-foreground">{metric.label}</h3>
                    <div className={`w-10 h-10 rounded-full ${metric.bgColor} flex items-center justify-center`}>
                      <metric.icon className={`w-5 h-5 ${metric.color}`} strokeWidth={2.5} />
                    </div>
                  </div>
                  <div className="text-4xl font-bold text-foreground mb-2">{metric.value}</div>
                  <Progress value={parseInt(metric.value)} className="h-2" />
                </div>
              ))}
            </div>

            <div className="glass-card rounded-2xl p-8 mb-8 animate-fade-in-up">
              <h3 className="text-2xl font-bold text-foreground mb-6">Key Insights</h3>
              <div className="space-y-4">
                {[
                  { 
                    icon: ThumbsUp, 
                    title: "Strong Product Satisfaction", 
                    description: "Customers praise ease of use and customer support",
                    sentiment: "positive"
                  },
                  { 
                    icon: MessageCircle, 
                    title: "Pricing Concerns", 
                    description: "Some feedback mentions pricing compared to competitors",
                    sentiment: "neutral"
                  },
                  { 
                    icon: ThumbsDown, 
                    title: "Feature Requests", 
                    description: "Users requesting mobile app improvements",
                    sentiment: "negative"
                  },
                ].map((insight, i) => (
                  <div key={i} className="flex items-start gap-4 p-4 rounded-lg bg-card/50 backdrop-blur-sm">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                      insight.sentiment === 'positive' ? 'bg-kelp/20' :
                      insight.sentiment === 'negative' ? 'bg-destructive/20' :
                      'bg-secondary'
                    }`}>
                      <insight.icon className={`w-5 h-5 ${
                        insight.sentiment === 'positive' ? 'text-kelp' :
                        insight.sentiment === 'negative' ? 'text-destructive' :
                        'text-foreground'
                      }`} />
                    </div>
                    <div>
                      <h4 className="font-semibold text-foreground mb-1">{insight.title}</h4>
                      <p className="text-sm text-foreground-secondary">{insight.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="glass-card rounded-2xl p-8 animate-fade-in-up">
              <h3 className="text-2xl font-bold text-foreground mb-6">Sentiment Distribution</h3>
              <div className="space-y-6">
                <div className="h-64 flex items-center justify-center bg-card/30 rounded-lg">
                  <p className="text-foreground-secondary">Sentiment trend chart over last 6 months</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="p-4 rounded-lg bg-card/30">
                    <h4 className="font-semibold text-foreground mb-2">Top Positive Keywords</h4>
                    <div className="flex flex-wrap gap-2">
                      {["excellent", "easy to use", "great support", "reliable", "efficient"].map((keyword) => (
                        <span key={keyword} className="px-3 py-1 rounded-full bg-primary/20 text-foreground dark:bg-kelp/20 dark:text-kelp text-sm">
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-card/30">
                    <h4 className="font-semibold text-foreground mb-2">Areas for Improvement</h4>
                    <div className="flex flex-wrap gap-2">
                      {["pricing", "mobile app", "loading speed", "export features"].map((keyword) => (
                        <span key={keyword} className="px-3 py-1 rounded-full bg-destructive/20 text-foreground dark:text-destructive text-sm font-semibold">
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default SentimentAnalysis;
