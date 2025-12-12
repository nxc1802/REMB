// API Service for SmartPlan AI v3.0

import {
    StateResponse,
    BlockInfo,
    GenerateRequest,
    GenerateResponse,
    ValidateRequest,
    ValidateResponse,
    FinalizeResponse,
} from '@/types/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003';

class ApiService {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE) {
        this.baseUrl = baseUrl;
    }

    private async fetch<T>(path: string, options?: RequestInit): Promise<T> {
        const response = await fetch(`${this.baseUrl}${path}`, {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // Health check
    async health(): Promise<{ status: string; version: string }> {
        return this.fetch('/health');
    }

    // Set boundary and extract blocks
    async setBoundary(
        boundary: number[][],
        roads: object[] = [],
        roadWidth: number = 12
    ): Promise<StateResponse> {
        return this.fetch('/api/set-boundary', {
            method: 'POST',
            body: JSON.stringify({ boundary, roads, road_width: roadWidth }),
        });
    }

    // Upload DXF file
    async uploadDXF(file: File, roadWidth: number = 12): Promise<StateResponse> {
        const formData = new FormData();
        formData.append('file', file);
        // Note: road_width is query param in some implementations but defined as body param in routes
        // For UploadFile, we need to pass additional data carefully. 
        // The current route definition: upload_dxf(file: UploadFile, road_width: float = 12.0)
        // FastAPI handles query params or form fields automatically. 
        // Let's assume road_width is a query param

        const response = await fetch(`${this.baseUrl}/api/upload-dxf?road_width=${roadWidth}`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // Get all blocks
    async getBlocks(): Promise<BlockInfo[]> {
        return this.fetch('/api/blocks');
    }

    // Get specific block
    async getBlock(blockId: string): Promise<BlockInfo> {
        return this.fetch(`/api/blocks/${blockId}`);
    }

    // Generate assets for a block using LLM
    async generateAssets(request: GenerateRequest): Promise<GenerateResponse> {
        return this.fetch(`/api/blocks/${request.block_id}/generate`, {
            method: 'POST',
            body: JSON.stringify(request),
        });
    }

    // Validate proposed assets
    async validateAssets(request: ValidateRequest): Promise<ValidateResponse> {
        return this.fetch('/api/validate', {
            method: 'POST',
            body: JSON.stringify(request),
        });
    }

    // Clear all assets from a block
    async clearAssets(blockId: string): Promise<{ status: string; cleared_count: number }> {
        return this.fetch(`/api/blocks/${blockId}/assets`, {
            method: 'DELETE',
        });
    }

    // Finalize and generate infrastructure
    async finalize(
        connectionPoint: number[],
        useSteiner: boolean = false
    ): Promise<FinalizeResponse> {
        return this.fetch('/api/finalize', {
            method: 'POST',
            body: JSON.stringify({
                connection_point: connectionPoint,
                use_steiner: useSteiner,
            }),
        });
    }

    // Get current state
    async getState(): Promise<StateResponse> {
        return this.fetch('/api/state');
    }

    // Reset state
    async reset(): Promise<{ status: string }> {
        return this.fetch('/api/reset', { method: 'DELETE' });
    }

    // Get available models
    async getModels(): Promise<{
        current_provider: string;
        current_model: string;
        providers: Record<string, { models: string[]; base_url?: string }>;
    }> {
        return this.fetch('/api/models');
    }

    // Switch model
    async switchModel(provider: string, model: string): Promise<{ status: string; provider: string; model: string }> {
        return this.fetch(`/api/models/switch?provider=${provider}&model=${model}`, { method: 'POST' });
    }

    // Export as JSON
    async exportJSON(): Promise<{ boundary: number[][] | null; blocks: any[] }> {
        return this.fetch('/api/export/json');
    }

    // Export as GeoJSON
    async exportGeoJSON(): Promise<{ type: string; features: any[] }> {
        return this.fetch('/api/export/geojson');
    }
}

export const api = new ApiService();
export default api;
