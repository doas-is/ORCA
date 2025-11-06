// src/services/api.ts
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

export interface CompanyAnalysis {
  domain: string;
  company: {
    name: string;
    description: string;
    niche: string | null;
    sector: string;
  };
  metadata: {
    pages_crawled: number;
    partner_indicators: string[];
    timestamp: string;
  };
  social: Record<string, string>;
  evidence: Array<{
    url: string;
    snippet: string;
    title: string;
  }>;
}

export interface Competitor {
  name: string;
  domain: string;
  rank?: number;
  da?: number;
  confidence?: string;
  overlap?: number;
  keywords?: number;
  articles?: number;
  description?: string;
  isNew?: boolean;
}

export interface CompetitorDiscoveryResult {
  competitors: Competitor[];
  statistics: {
    total_found: number;
    high_confidence: number;
    medium_confidence: number;
    low_confidence: number;
  };
  metadata?: {
    timestamp: string;
    query_data: any;
  };
}

class APIService {
  /**
   * Enhanced fetch with configurable timeout and keepalive
   * @param url - Target URL
   * @param options - Fetch options
   * @param timeout - Timeout in milliseconds
   */
  private async fetchWithTimeout(url: string, options: RequestInit, timeout = 120000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        // Enable keepalive to prevent connection drops on long requests
        keepalive: true,
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error: any) {
      clearTimeout(timeoutId);
      
      // Better error handling for timeouts
      if (error.name === 'AbortError') {
        throw new Error(
          `Request timeout after ${timeout / 1000} seconds. ` +
          `The backend may still be processing - check Flask terminal for progress.`
        );
      }
      
      throw error;
    }
  }

  /**
   * Analyze a company URL
   * Timeout: 2 minutes (sufficient for web crawling)
   */
  async analyzeUrl(url: string, maxPages: number = 30): Promise<CompanyAnalysis> {
    try {
      console.log('🔍 Analyzing URL:', url);
      console.log('📡 API Endpoint:', `${API_BASE_URL}/analyze-url`);
      
      const response = await this.fetchWithTimeout(
        `${API_BASE_URL}/analyze-url`,  // FIXED: Changed from /analyze to /analyze-url
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ url, max_pages: maxPages }),
        },
        120000 // 2 minutes
      );

      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(error.error || `Analysis failed: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Handle the response structure from Flask (success/data wrapper)
      if (data.success === false) {
        throw new Error(data.error || 'Analysis failed');
      }
      
      // If wrapped in success/data structure, extract the data
      const result = data.data || data;
      
      console.log('✅ Analysis complete:', result);
      return result;
    } catch (error: any) {
      console.error('❌ Analysis error:', error);
      
      // More helpful error messages
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        throw new Error('Cannot connect to Flask backend. Make sure it is running on port 5000.');
      }
      
      throw error;
    }
  }

  /**
   * Discover competitors (LONG RUNNING OPERATION)
   * Timeout: 10 minutes (searches Google, crawls multiple sites, runs AI analysis)
   */
  async discoverCompetitors(
    companyData: CompanyAnalysis,
    target: number = 10
  ): Promise<CompetitorDiscoveryResult> {
    try {
      console.log('🔍 Discovering competitors for:', companyData.company.name);
      console.log(`⏱️  This may take several minutes - searching for ${target} competitors...`);
      console.log('📡 API Endpoint:', `${API_BASE_URL}/discover-competitors`);
      
      const response = await this.fetchWithTimeout(
        `${API_BASE_URL}/discover-competitors`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
            company_data: companyData,
            target 
          }),
        },
        600000 // 10 MINUTES - increased from 2 minutes!
      );

      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(error.error || `Discovery failed: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Handle the response structure from Flask (success/data wrapper)
      if (data.success === false) {
        throw new Error(data.error || 'Discovery failed');
      }
      
      // If wrapped in success/data structure, extract the data
      const result = data.data || data;
      
      console.log('✅ Competitors discovered:', result);
      console.log(`📊 Found ${result.statistics?.total_found || 0} competitors`);
      return result;
    } catch (error: any) {
      console.error('❌ Competitor discovery error:', error);
      
      // Provide helpful error messages
      if (error.message.includes('timeout')) {
        throw new Error(
          'Discovery is taking longer than expected (>10 minutes). ' +
          'The backend is likely still processing. Check the Flask terminal ' +
          'to see if the agent is still running. You may need to restart the analysis.'
        );
      }
      
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        throw new Error('Lost connection to Flask backend during discovery. Make sure it is still running.');
      }
      
      throw error;
    }
  }

  /**
   * Health check to verify backend is available
   */
  async checkHealth(): Promise<{ 
    status: string; 
    service?: string;
  }> {
    try {
      // Remove /api from base URL for health check
      const healthUrl = API_BASE_URL.replace('/api', '/health');
      console.log('🏥 Health check:', healthUrl);
      
      const response = await fetch(healthUrl, {
        method: 'GET',
      });
      
      if (!response.ok) {
        throw new Error('Health check failed');
      }
      
      const data = await response.json();
      console.log('✅ Backend health:', data);
      return data;
    } catch (error) {
      console.error('❌ Health check failed - Flask server may not be running:', error);
      throw new Error('Cannot connect to Flask backend. Make sure it is running on port 5000.');
    }
  }
}

export const apiService = new APIService();