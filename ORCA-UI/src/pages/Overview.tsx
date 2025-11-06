import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Building2, Plus, X, Waves, AlertCircle, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { apiService, CompanyAnalysis } from "@/services/api";
import { useAnalysis } from "@/contexts/AnalysisContext";
import { useToast } from "@/components/Toast";

const Overview = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const {
    companyData,
    setCompanyData,
    isLoading,
    setIsLoading,
    error,
    setError,
    reset,
    currentAnalysisStep,
    setCurrentAnalysisStep,
  } = useAnalysis();

  const [url, setUrl] = useState("");
  const [competitors, setCompetitors] = useState<string[]>([]);
  const [newCompetitor, setNewCompetitor] = useState("");
  const [animatingOut, setAnimatingOut] = useState<number | null>(null);
  const [isValid, setIsValid] = useState(true);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  
  const [checkmarks, setCheckmarks] = useState<boolean[]>([false, false, false]);

  // Determine current view based on context state
  const currentStep = companyData ? 3 : currentAnalysisStep || 1;

  const validateUrl = (value: string) => {
    const urlPattern = /^https?:\/\/.+\..+/;
    setIsValid(value === "" || urlPattern.test(value));
    setUrl(value);
  };

  const addCompetitor = () => {
    if (newCompetitor.trim()) {
      setCompetitors([...competitors, newCompetitor]);
      setNewCompetitor("");
    }
  };

  const removeCompetitor = (index: number) => {
    setAnimatingOut(index);
    setTimeout(() => {
      setCompetitors(competitors.filter((_, i) => i !== index));
      setAnimatingOut(null);
    }, 300);
  };

  const handleAnalyze = async () => {
    if (!url || !isValid) return;
    
    setError(null);
    setCurrentAnalysisStep(2);
    setIsLoading(true);
    setAnalysisProgress(0);
    setCheckmarks([false, false, false]);

    // Simulate progress
    const progressInterval = setInterval(() => {
      setAnalysisProgress(prev => Math.min(prev + 1, 90));
    }, 100);

    setTimeout(() => setCheckmarks([true, false, false]), 800);
    setTimeout(() => setCheckmarks([true, true, false]), 1400);

    try {
      // Call backend
      const result = await apiService.analyzeUrl(url, 30);
      setCompanyData(result);
      
      setCheckmarks([true, true, true]);
      clearInterval(progressInterval);
      setAnalysisProgress(100);
      
      setTimeout(() => {
        setIsLoading(false);
        setCurrentAnalysisStep(3);
        showToast("✅ Analysis complete! Review your company profile.", "success");
      }, 500);
    } catch (err: any) {
      clearInterval(progressInterval);
      setError(err.message || 'Failed to analyze website');
      setIsLoading(false);
      setCurrentAnalysisStep(1);
      showToast("❌ Analysis failed. Please try again.", "error");
    }
  };

  const handleNewAnalysis = () => {
    reset();
    setUrl("");
    setCompetitors([]);
    setCurrentAnalysisStep(1);
    showToast("🔄 Starting new analysis...", "info");
  };

  const handleDiscoverCompetitors = () => {
    navigate("/content-strategy");
    showToast("🔍 Discovering competitors in your market...", "info");
  };

  return (
    <div className="relative min-h-screen pt-24 pb-16">
      <div className="ocean-gradient absolute inset-0" style={{ zIndex: -1 }} />
      <div className="relative z-10">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-5xl">
          
          {/* Error Display */}
          {error && (
            <div className="mb-6 glass-card rounded-xl p-4 border-2 border-red-500/50 animate-fade-in">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h3 className="font-semibold text-red-500 mb-1">Error</h3>
                  <p className="text-sm text-foreground-secondary">{error}</p>
                </div>
                <button onClick={() => setError(null)} className="text-foreground-secondary hover:text-foreground">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Step 1: Initial Input */}
          {currentStep === 1 && (
            <div className="animate-fade-in space-y-8">
              <div className="text-center space-y-4">
                <div className="flex items-center justify-center space-x-3 mb-6">
                  <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center">
                    <Waves className="w-7 h-7 text-primary" />
                  </div>
                  <h1 className="text-5xl font-bold text-foreground">ORCA</h1>
                </div>
                <p className="text-xl text-foreground-secondary">
                  Automated competitor extraction • Dive deep, surface insights
                </p>
              </div>

              <div className="glass-card rounded-2xl p-8 space-y-6">
                <h2 className="text-2xl font-bold text-foreground">Step 1: Enter Your Website</h2>
                
                <Input
                  type="url"
                  placeholder="https://example.com"
                  value={url}
                  onChange={(e) => validateUrl(e.target.value)}
                  className={`text-lg h-14 ${!isValid ? "border-destructive" : ""}`}
                />
                
                <Button
                  onClick={handleAnalyze}
                  disabled={!url || !isValid || isLoading}
                  className="w-full h-14 text-lg bg-primary hover:bg-primary/90 text-primary-foreground font-semibold"
                >
                  Analyze Market <ArrowRight className="ml-2" />
                </Button>

                <div className="pt-6 border-t border-border">
                  <p className="text-foreground-secondary mb-4">
                    Optional: Know your competitors? Add them here
                  </p>
                  
                  <div className="space-y-3">
                    <div className="flex gap-2">
                      <Input
                        type="url"
                        placeholder="Competitor URL"
                        value={newCompetitor}
                        onChange={(e) => setNewCompetitor(e.target.value)}
                        onKeyPress={(e) => e.key === "Enter" && addCompetitor()}
                        className="flex-1"
                      />
                      <Button onClick={addCompetitor} variant="outline" size="icon" className="shrink-0">
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>

                    {competitors.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-2">
                        {competitors.map((comp, index) => (
                          <div
                            key={index}
                            className={`
                              group relative inline-flex items-center gap-2 px-4 py-2 
                              rounded-full bg-primary/30 border border-primary/50
                              transition-all duration-300
                              ${animatingOut === index ? 'opacity-0 scale-75' : 'opacity-100 scale-100'}
                            `}
                          >
                            <span className="text-sm text-foreground">{comp}</span>
                            <button
                              onClick={() => removeCompetitor(index)}
                              className="opacity-0 group-hover:opacity-100 transition-opacity"
                              aria-label="Remove competitor"
                            >
                              <X className="w-3 h-3 text-foreground" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Analysis Loading */}
          {currentStep === 2 && (
            <div className="animate-fade-in glass-card rounded-2xl p-8 max-w-2xl mx-auto">
              <h2 className="text-2xl font-bold text-foreground mb-6">Analyzing Your Market...</h2>
              
              <div className="space-y-4 mb-6">
                {[
                  "Crawling your website...",
                  "Understanding your business...",
                  "Identifying your market..."
                ].map((text, i) => (
                  <div key={i} className="flex items-center gap-3 animate-fade-in" style={{ animationDelay: `${i * 300}ms` }}>
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
                This may take 1-2 minutes...
              </p>
            </div>
          )}

          {/* Step 3: Business Summary */}
          {currentStep === 3 && companyData && (
            <div className="animate-fade-in-up space-y-6">
              <div className="glass-card rounded-2xl p-8">
                <h2 className="text-2xl font-bold text-foreground mb-6">Here's What We Found</h2>
                
                <div className="space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                      <Building2 className="w-6 h-6 text-primary" />
                    </div>
                    <div className="flex-1">
                      <p className="text-foreground-secondary mb-2">Your company:</p>
                      <h3 className="text-2xl font-bold text-foreground mb-3">
                        {companyData.company.name}
                      </h3>
                      <p className="text-foreground-secondary mb-4">
                        {companyData.company.description}
                      </p>
                      
                      {companyData.company.niche && (
                        <div className="mb-4">
                          <p className="text-sm text-foreground-secondary mb-2">Industry:</p>
                          <div className="flex flex-wrap gap-2">
                            {companyData.company.niche.split(',').map((topic, i) => (
                              <span
                                key={i}
                                className="px-3 py-1 rounded-full bg-primary/20 text-white dark:text-primary text-sm font-medium"
                              >
                                {topic.trim()}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      <div className="text-sm text-foreground-secondary space-y-1">
                        <p>📊 Pages analyzed: {companyData.metadata.pages_crawled}</p>
                        <p>🏢 Sector: {companyData.company.sector}</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3 mt-6">
                  <Button
                    onClick={handleNewAnalysis}
                    variant="outline"
                    className="flex-1"
                  >
                    New Analysis
                  </Button>
                  <Button
                    onClick={handleDiscoverCompetitors}
                    disabled={isLoading}
                    className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground"
                  >
                    Discover Competitors <ArrowRight className="ml-2" />
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Overview;