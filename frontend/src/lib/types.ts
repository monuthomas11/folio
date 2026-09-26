export type HoldingStatus = "healthy" | "near-sl" | "sl-hit" | "target-hit";

export type AlertKind =
  | "sl-hit"
  | "target-hit"
  | "entry-reached"
  | "target-reached"
  | "stop-loss-hit"
  | "invalidation-hit";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
}

export interface ApiKey {
  id: string;
  name: string;
  keyPrefix: string;
  lastUsedAt: string | null;
  revokedAt: string | null;
  createdAt: string;
}

export interface CreatedApiKey extends ApiKey {
  key: string;
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
  oneDayChangePct: number | null;
  lastUpdated: string | null;
}

export interface HoldingExit {
  id: string;
  symbol: string;
  quantity: number;
  avgBuyPrice: number;
  exitPrice: number;
  costBasis: number;
  proceeds: number;
  realizedPnl: number;
  broker: string | null;
  exitedAt: string;
}

export interface PortfolioAlert {
  id: string;
  holdingId: string | null;
  watchlistItemId: string | null;
  watchlistLevelId: string | null;
  symbol: string;
  kind: AlertKind;
  price: number;
  message: string | null;
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
  realizedPnl: number;
  realizedPnlPct: number;
  realizedCostBasis: number;
  realizedProceeds: number;
  closedTradeCount: number;
}

export interface PortfolioSnapshot {
  summary: PortfolioSummary;
  holdings: Holding[];
  alerts: PortfolioAlert[];
  realizedExits: HoldingExit[];
}

export type TradeSide = "long" | "short";
export type TradeStatus = "open" | "closed";
export type TradeAssetClass = "equity" | "fno";
export type TradeInstrumentType = "equity" | "future" | "option";
export type TradeExchange = "NSE" | "BSE";
export type TradeUnderlyingType = "index" | "stock";
export type TradeOptionType = "CE" | "PE";

export interface TradeChargesInput {
  brokerage: number | null;
  sttCtt: number | null;
  exchangeTransaction: number | null;
  sebi: number | null;
  gst: number | null;
  stampDuty: number | null;
  ipft: number | null;
  other: number | null;
  contractNoteRef: string | null;
}

export interface TradeCharges {
  id: string;
  legType: "entry" | "exit";
  brokerage: number | null;
  sttCtt: number | null;
  exchangeTransaction: number | null;
  sebi: number | null;
  gst: number | null;
  stampDuty: number | null;
  ipft: number | null;
  other: number | null;
  contractNoteRef: string | null;
  total: number | null;
  complete: boolean;
}

export interface TradeExit {
  id: string;
  quantity: number;
  exitLots: number | null;
  exitPrice: number;
  exitDate: string;
  exitAt: string | null;
  exitReason: string | null;
  exitOrderId: string | null;
  exitContractNoteRef: string | null;
  notes: string | null;
  realizedPnl: number;
  grossRealizedPnl: number;
  netRealizedPnl: number | null;
  charges: TradeCharges | null;
}

export interface Trade {
  id: string;
  symbol: string;
  side: TradeSide;
  assetClass: TradeAssetClass;
  instrumentType: TradeInstrumentType;
  exchange: TradeExchange | null;
  underlyingType: TradeUnderlyingType | null;
  underlyingSymbol: string | null;
  contractSymbol: string | null;
  expiryDate: string | null;
  strikePrice: number | null;
  tickSize: number | null;
  optionType: TradeOptionType | null;
  lotSize: number | null;
  entryLots: number | null;
  remainingLots: number | null;
  entryAt: string | null;
  entryOrderId: string | null;
  entryContractNoteRef: string | null;
  strategy: string | null;
  thesis: string | null;
  settlementType: string | null;
  productType: string | null;
  marginUsed: number | null;
  entryDate: string;
  entryQuantity: number;
  entryPrice: number;
  broker: string | null;
  notes: string | null;
  currentLtp: number | null;
  markSource: string | null;
  lastUpdated: string | null;
  remainingQuantity: number;
  grossEntryValue: number;
  grossRealizedPnl: number;
  grossUnrealizedPnl: number | null;
  grossTotalPnl: number | null;
  netRealizedPnl: number | null;
  netUnrealizedPnl: number | null;
  netTotalPnl: number | null;
  entryCharges: number | null;
  entryCharge: TradeCharges | null;
  exitCharges: number | null;
  totalCharges: number | null;
  chargesComplete: boolean;
  capitalBasis: number | null;
  openExposure: number | null;
  status: TradeStatus;
  realizedPnl: number;
  unrealizedPnl: number | null;
  totalPnl: number | null;
  exits: TradeExit[];
}

export interface TradeInput {
  symbol: string;
  side: TradeSide;
  assetClass: TradeAssetClass;
  instrumentType: TradeInstrumentType;
  exchange: TradeExchange | null;
  underlyingType: TradeUnderlyingType | null;
  underlyingSymbol: string | null;
  contractSymbol: string | null;
  expiryDate: string | null;
  strikePrice: number | null;
  tickSize: number | null;
  optionType: TradeOptionType | null;
  lotSize: number | null;
  entryLots: number | null;
  productType: string | null;
  entryAt: string | null;
  entryOrderId: string | null;
  entryContractNoteRef: string | null;
  strategy: string | null;
  thesis: string | null;
  settlementType: string | null;
  marginUsed: number | null;
  entryDate: string;
  entryQuantity: number | null;
  entryPrice: number;
  broker: string | null;
  notes: string | null;
  entryCharges: TradeChargesInput | null;
}

export interface TradeExitInput {
  quantity: number | null;
  exitLots: number | null;
  exitPrice: number;
  exitDate: string;
  exitAt: string | null;
  exitReason: string | null;
  exitOrderId: string | null;
  exitContractNoteRef: string | null;
  notes: string | null;
  charges: TradeChargesInput | null;
}

export interface TradebookSummary {
  tradeCount: number;
  openCount: number;
  closedCount: number;
  realizedPnl: number;
  unrealizedPnl: number | null;
  totalPnl: number | null;
  unpricedOpenCount: number;
  grossRealizedPnl: number;
  grossUnrealizedPnl: number | null;
  grossTotalPnl: number | null;
  netRealizedPnl: number | null;
  netUnrealizedPnl: number | null;
  netTotalPnl: number | null;
  totalCharges: number | null;
  openExposure: number | null;
  incompleteChargeCount: number;
  winRate: number | null;
}

export interface TradebookData {
  summary: TradebookSummary;
  trades: Trade[];
  quoteErrors: { tradeId: string; symbol: string; message: string }[];
}

export interface TradeMarkInput {
  ltp: number;
  source: "manual" | "exchange";
}

export type WatchlistLevelKind = "entry" | "target" | "stop-loss" | "invalidation";

export interface WatchlistLevel {
  id: string;
  kind: WatchlistLevelKind;
  label: string | null;
  lowerPrice: number;
  upperPrice: number | null;
  sortOrder: number;
  conditionMet: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface WatchlistLevelInput {
  kind: WatchlistLevelKind;
  label: string | null;
  lowerPrice: number;
  upperPrice: number | null;
}

export interface WatchlistItem {
  id: string;
  symbol: string;
  notes: string | null;
  currentLtp: number | null;
  lastUpdated: string | null;
  createdAt: string;
  updatedAt: string;
  levels: WatchlistLevel[];
}

export interface WatchlistInput {
  symbol: string;
  notes: string | null;
  levels: WatchlistLevelInput[];
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

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatRequest {
  context: "holding" | "portfolio";
  holdingId?: string;
  message: string;
  history: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
  provider: string;
  modelName: string | null;
}
