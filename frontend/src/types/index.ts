// Type definitions for AIOptimize MVP

export interface Coordinates {
  x: number;
  y: number;
}

export interface PlotData {
  x: number;
  y: number;
  width: number;
  height: number;
  area: number;
  coords: number[][];
}

export interface LayoutMetrics {
  total_plots: number;
  total_area: number;
  avg_size: number;
  fitness: number;
  compliance: string;
}

export interface LayoutOption {
  id: number;
  name: string;
  icon: string;
  description: string;
  plots: PlotData[];
  metrics: LayoutMetrics;
}

export interface SiteMetadata {
  area: number;
  perimeter: number;
  bounds: number[];
  centroid: number[];
}

export interface GeoJSONGeometry {
  type: string;
  coordinates: number[][][];
}

export interface GeoJSONFeature {
  type: string;
  geometry: GeoJSONGeometry;
  properties?: Record<string, unknown>;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  model?: string;
  timestamp?: string;
}

export interface UploadResponse {
  session_id: string;
  boundary: GeoJSONFeature;
  metadata: SiteMetadata;
}

export interface GenerateResponse {
  session_id: string;
  options: LayoutOption[];
  count: number;
}

export interface ChatResponse {
  message: string;
  model: 'gemini-2.0-flash' | 'fallback';
}

export interface AppState {
  sessionId: string | null;
  boundary: GeoJSONFeature | null;
  boundaryCoords: number[][] | null;
  metadata: SiteMetadata | null;
  options: LayoutOption[];
  selectedOption: number | null;
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
}
