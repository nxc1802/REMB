// API Types for SmartPlan AI v3.0

export interface Coordinate {
    0: number;
    1: number;
}

export interface AssetInfo {
    type: string;
    polygon: number[][];
}

export interface BlockInfo {
    id: string;
    polygon: number[][];
    area: number;
    assets: AssetInfo[];
}

export interface StateResponse {
    boundary: number[][] | null;
    blocks: BlockInfo[];
    total_area: number;
    used_area: number;
    coverage_ratio: number;
}

export interface GenerateRequest {
    block_id: string;
    user_request: string;
}

export interface GenerateResponse {
    success: boolean;
    action: 'add' | 'clear' | 'replace';
    new_assets: AssetInfo[];
    explanation: string;
    error: string | null;
}

export interface ValidateRequest {
    block_id: string;
    new_assets: AssetInfo[];
}

export interface ValidateResponse {
    success: boolean;
    merged_assets: AssetInfo[];
    errors: string[];
    warnings: string[];
}

export interface InfrastructureLine {
    type: string;
    id: string;
    coordinates: number[][];
    length: number;
}

export interface TransformerPoint {
    id: string;
    coordinates: number[];
}

export interface DrainageArrow {
    id: string;
    start: number[];
    end: number[];
}

export interface FinalizeResponse {
    success: boolean;
    electric_lines: InfrastructureLine[];
    water_lines: InfrastructureLine[];
    total_electric_length: number;
    total_water_length: number;
    transformers: TransformerPoint[];
    drainage_arrows: DrainageArrow[];
    redundant_edges: number;
    error: string | null;
    geojson?: any;
}
