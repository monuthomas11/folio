export type HoldingStatus = "healthy" | "near-sl" | "sl-hit" | "target-hit";

export type AlertKind = "sl-hit" | "target-hit";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
}

export interface Holding {
  id: string;
  symbol: string;
  quantity: number;
  avgBuyPrice: number;
  stopLoss: number | null;
  targetPrice: number | null;
  broker: string | null;
  sector: string | null;
  currentLtp: number | null;
  lastUpdated: string | null;
}

export interface PortfolioAlert {
  id: string;
  holdingId: string;
  symbol: string;
  kind: AlertKind;
  price: number;
  createdAt: string;
  dismissed: boolean;
}

export interface HoldingsInput {
  symbol: string;
  quantity: number;
  avgBuyPrice: number;
  stopLoss: number | null;
  targetPrice: number | null;
  broker: string | null;
  sector: string | null;
}

export interface PortfolioSummary {
  portfolioValue: number;
  invested: number;
  totalPnl: number;
  totalPnlPct: number;
  holdingCount: number;
  activeAlertCount: number;
  gainers: number;
  losers: number;
}

export interface PortfolioSnapshot {
  summary: PortfolioSummary;
  holdings: Holding[];
  alerts: PortfolioAlert[];
}

export interface ImportRowError {
  row: number;
  message: string;
}

export interface ImportResult {
  created: number;
  errors: ImportRowError[];
}

export type AnalysisRating = "BUY" | "HOLD" | "REDUCE" | "EXIT";

export interface InvestmentProfile {
  investmentStyle: string;
  riskTolerance: string;
  investmentHorizon: string;
  maxSingleStockWeight: number;
  maxSectorWeight: number;
  warnSingleStockWeight: number;
  warnSectorWeight: number;
  updatedAt: string;
}

export interface InvestmentProfileInput {
  investmentStyle?: string;
  riskTolerance?: string;
  investmentHorizon?: string;
  maxSingleStockWeight?: number;
  maxSectorWeight?: number;
  warnSingleStockWeight?: number;
  warnSectorWeight?: number;
}

export type AnalysisRunStatus =
  | "CREATED"
  | "RUNNING"
  | "COMPLETED"
  | "PARTIAL_COMPLETION"
  | "FAILED";

export interface AnalysisRun {
  id: string;
  kind: "holding" | "portfolio";
  holdingId: string | null;
  status: AnalysisRunStatus;
  stage: string | null;
  provider: string;
  modelName: string | null;
  errorMessage: string | null;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
}

export interface AnalysisRunDetail extends AnalysisRun {
  recommendationIds: string[];
}

export interface RecommendationScores {
  businessQuality?: number | null;
  fundamental?: number | null;
  valuation?: number | null;
  technical?: number | null;
  portfolioFit?: number | null;
}

export interface FairValueRange {
  low: number | null;
  base: number | null;
  high: number | null;
}

export interface Recommendation {
  id: string;
  runId: string;
  holdingId: string | null;
  kind: "holding" | "portfolio";
  symbol: string;
  rating: AnalysisRating;
  action: string;
  confidence: number | null;
  scores: RecommendationScores | null;
  portfolioWeight: number | null;
  thesisStatus: string | null;
  summary: string;
  why: string | null;
  bullCase: string | null;
  baseCase: string | null;
  bearCase: string | null;
  keyReasons: string[];
  keyRisks: string[];
  buyConditions: string[];
  reduceConditions: string[];
  exitConditions: string[];
  supportLevels: number[];
  resistanceLevels: number[];
  fairValueRange: FairValueRange | null;
  evidenceIds: string[];
  evidence: EvidenceItem[] | null;
  dataQuality: string;
  qualityFlags: string[];
  healthScore: number | null;
  positives: string[];
  concerns: string[];
  priorityNote: string | null;
  analysisTimestamps: {
    generatedAt?: string;
    marketDataThrough?: string;
    note?: string;
  } | null;
  createdAt: string;
}

export interface LatestAnalysisRunInfo {
  provider: string;
  modelName: string | null;
  completedAt: string | null;
  createdAt: string;
}

export interface LatestPortfolioAnalysis {
  portfolio: Recommendation | null;
  holdings: Recommendation[];
  lastRun: LatestAnalysisRunInfo | null;
}

export interface EvidenceItem {
  id: string;
  category: string;
  label: string;
  value: unknown;
  unit: string | null;
  source: string;
  observedAt: string | null;
  freshness: string;
  confidence: string;
  note: string | null;
}