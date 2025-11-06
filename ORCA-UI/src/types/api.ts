/**
 * TypeScript types for ORCA API
 * Mirrors the JSON structures from Python agents
 */

// ==================== Company Analysis Types ====================
export interface CompanyData {
  domain: string;
  start_url: string;
  company: {
    name: string;
    description: string;
    sector: string;
    niche: string;
  };
  evidence: Array<{
    url: string;
    snippet: string;
    title: string;
  }>;
  metadata: {
    pages_crawled: number;
    timestamp: string;
    partner_indicators: string[];
    client_indicators: string[];
  };
  social: Record<string, string>;
}

// ==================== Competitor Discovery Types ====================
export interface CompetitorContext {
  niche: string;
  sector: string;
  location: string;
}

export interface CompetitorStatistics {
  total_found: number;
  direct: number;
  strong: number;
  moderate: number;
  weak: number;
  average_score: number;
  ai_rejections: number;
}

export interface CompetitorBreakdown {
  ai_analysis: {
    score: number;
    points: number;
    max: number;
    reasoning: string;
  };
  keyword_overlap: {
    score: number;
    points: number;
    max: number;
  };
  business_model: {
    score: number;
    points: number;
    max: number;
  };
  social_presence: {
    points: number;
    max: number;
  };
  content_quality: {
    points: number;
    max: number;
  };
}

export interface Competitor {
  input_url: string;
  domain: string;
  fetched_at: string;
  company: {
    name: string;
    description: string;
    location: string;
    is_local: boolean;
  };
  social: Record<string, string>;
  evidence: any[];
  snippet: string;
  score: number;
  tier: string;
  breakdown: CompetitorBreakdown;
}

export interface AIRejection {
  name: string;
  domain: string;
  reason: string;
  ai_score: number;
}

export interface CompetitorDiscoveryResult {
  source_company: string;
  analysis_date: string;
  context: CompetitorContext;
  statistics: CompetitorStatistics;
  competitors: Competitor[];
  ai_rejections: AIRejection[];
}

// ==================== API Response Types ====================
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface AnalyzeUrlRequest {
  url: string;
  max_pages?: number;
}

export interface DiscoverCompetitorsRequest {
  company_data: CompanyData;
  target?: number;
}

// ==================== API Error Types ====================
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public response?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}