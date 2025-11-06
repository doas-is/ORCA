import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import ThemeToggle from "./components/ThemeToggle";
import BubbleBackground from "./components/BubbleBackground";
import AmbientBubbles from "./components/AmbientBubbles";
import { AnalysisProvider } from "./contexts/AnalysisContext";
import { ToastProvider } from "./components/Toast";
import Overview from "./pages/Overview";
import ContentStrategy from "./pages/ContentStrategy";
import SentimentAnalysis from "./pages/SentimentAnalysis";
import QuickAudit from "./pages/QuickAudit";
import Insights from "./pages/Insights";
import GapAnalysis from "./pages/GapAnalysis";
import ExportReport from "./pages/ExportReport";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <ToastProvider>
        <AnalysisProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <div className="relative min-h-screen">
              {/* Background Effects Layer */}
              <BubbleBackground />
              <AmbientBubbles />
              
              {/* UI Layer */}
              <Navbar />
              <ThemeToggle />
              
              {/* Content Layer */}
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/content-strategy" element={<ContentStrategy />} />
                <Route path="/sentiment" element={<SentimentAnalysis />} />
                <Route path="/quick-audit" element={<QuickAudit />} />
                <Route path="/insights" element={<Insights />} />
                <Route path="/gap-analysis" element={<GapAnalysis />} />
                <Route path="/export" element={<ExportReport />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </div>
          </BrowserRouter>
        </AnalysisProvider>
      </ToastProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;