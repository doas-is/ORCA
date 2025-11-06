import { Link, useLocation } from "react-router-dom";
import { Waves, Loader2 } from "lucide-react";
import { useAnalysis } from "@/contexts/AnalysisContext";

const Navbar = () => {
  const location = useLocation();
  const { isLoading } = useAnalysis();

  const navItems = [
    { path: "/", label: "Overview" },
    { path: "/content-strategy", label: "Competitors" },
    { path: "/sentiment", label: "Market Analysis" },
    { path: "/quick-audit", label: "Quick Audit" },
    { path: "/insights", label: "Strategic Insights" },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-card/80 backdrop-blur-lg border-b border-border">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link 
            to="/" 
            className={`flex items-center space-x-2 group ${isLoading ? 'pointer-events-none opacity-50' : ''}`}
            onClick={(e) => isLoading && e.preventDefault()}
          >
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center group-hover:bg-primary/30 transition-colors">
              {isLoading ? (
                <Loader2 className="w-5 h-5 text-primary animate-spin" />
              ) : (
                <Waves className="w-5 h-5 text-primary" />
              )}
            </div>
            <span className="text-xl font-bold text-foreground">ORCA</span>
          </Link>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              const isDisabled = isLoading;
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={(e) => {
                    if (isDisabled) {
                      e.preventDefault();
                    }
                  }}
                  className={`
                    relative px-4 py-2 rounded-lg text-sm font-medium transition-all
                    ${isDisabled ? 'opacity-40 cursor-not-allowed' : ''}
                    ${
                      isActive && !isDisabled
                        ? "bg-primary/20 text-primary shadow-[0_4px_0_0_rgba(59,130,246,0.8),0_0_20px_rgba(59,130,246,0.4)] translate-y-[-2px]"
                        : isDisabled
                        ? "text-foreground-secondary"
                        : "text-foreground-secondary hover:text-foreground hover:bg-secondary/50 hover:translate-y-[-1px] hover:shadow-[0_2px_0_0_rgba(59,130,246,0.5),0_0_10px_rgba(59,130,246,0.2)]"
                    }
                  `}
                  style={{
                    transition: 'all 0.2s ease'
                  }}
                  title={isDisabled ? "Analysis in progress..." : ""}
                >
                  {item.label}
                </Link>
              );
            })}
            
            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex items-center gap-2 px-4 py-2 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
                <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />
                <span className="text-xs text-yellow-400 font-medium">Analyzing...</span>
              </div>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden">
            <button 
              className={`text-foreground-secondary hover:text-foreground ${isLoading ? 'opacity-50 pointer-events-none' : ''}`}
              disabled={isLoading}
            >
              <svg
                className="w-6 h-6"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path d="M4 6h16M4 12h16M4 18h16"></path>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;