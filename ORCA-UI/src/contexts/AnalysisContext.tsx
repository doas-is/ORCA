import React, { createContext, useContext, useState } from 'react';
import { CompanyAnalysis, CompetitorDiscoveryResult } from '@/services/api';

interface AnalysisContextType {
  companyData: CompanyAnalysis | null;
  setCompanyData: (data: CompanyAnalysis | null) => void;
  competitorData: CompetitorDiscoveryResult | null;
  setCompetitorData: (data: CompetitorDiscoveryResult | null) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
  reset: () => void;
  
  // Step completion tracking
  isStep1Complete: boolean;
  isStep2Complete: boolean;
  currentAnalysisStep: number;
  setCurrentAnalysisStep: (step: number) => void;
}

const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined);

export const AnalysisProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [companyData, setCompanyData] = useState<CompanyAnalysis | null>(null);
  const [competitorData, setCompetitorData] = useState<CompetitorDiscoveryResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentAnalysisStep, setCurrentAnalysisStep] = useState(0);

  // Computed properties for step completion
  const isStep1Complete = companyData !== null;
  const isStep2Complete = competitorData !== null;

  const reset = () => {
    setCompanyData(null);
    setCompetitorData(null);
    setIsLoading(false);
    setError(null);
    setCurrentAnalysisStep(0);
  };

  return (
    <AnalysisContext.Provider
      value={{
        companyData,
        setCompanyData,
        competitorData,
        setCompetitorData,
        isLoading,
        setIsLoading,
        error,
        setError,
        reset,
        isStep1Complete,
        isStep2Complete,
        currentAnalysisStep,
        setCurrentAnalysisStep,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  );
};

export const useAnalysis = () => {
  const context = useContext(AnalysisContext);
  if (context === undefined) {
    throw new Error('useAnalysis must be used within an AnalysisProvider');
  }
  return context;
};