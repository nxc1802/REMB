// API service for AIOptimize

import axios from 'axios';
import type {
    UploadResponse,
    GenerateResponse,
    ChatResponse,
    GeoJSONFeature
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const apiService = {
    // Health check
    async health() {
        const response = await api.get('/api/health');
        return response.data;
    },

    // Get sample data
    async getSampleData(): Promise<GeoJSONFeature> {
        const response = await api.get('/api/sample-data');
        return response.data;
    },

    // Upload boundary (JSON)
    async uploadBoundary(geojson: GeoJSONFeature): Promise<UploadResponse> {
        const response = await api.post('/api/upload-boundary-json', {
            geojson: geojson,
        });
        return response.data;
    },

    // Upload boundary file (DXF or GeoJSON)
    async uploadBoundaryFile(file: File): Promise<UploadResponse> {
        const formData = new FormData();
        formData.append('file', file);

        // Use DXF endpoint for .dxf files
        const isDxf = file.name.toLowerCase().endsWith('.dxf');
        const endpoint = isDxf ? '/api/upload-dxf' : '/api/upload-boundary';

        const response = await api.post(endpoint, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    },

    // Generate layouts
    async generateLayouts(
        sessionId: string,
        targetPlots: number = 8,
        setback: number = 50
    ): Promise<GenerateResponse> {
        const response = await api.post('/api/generate-layouts', {
            session_id: sessionId,
            target_plots: targetPlots,
            setback: setback,
        });
        return response.data;
    },

    // Chat
    async chat(sessionId: string, message: string): Promise<ChatResponse> {
        const response = await api.post('/api/chat', {
            session_id: sessionId,
            message: message,
        });
        return response.data;
    },

    // Export DXF
    async exportDxf(sessionId: string, optionId: number): Promise<Blob> {
        const response = await api.post('/api/export-dxf', {
            session_id: sessionId,
            option_id: optionId,
        }, {
            responseType: 'blob',
        });
        return response.data;
    },

    // Export all as ZIP
    async exportAllDxf(sessionId: string): Promise<Blob> {
        const formData = new FormData();
        formData.append('session_id', sessionId);

        const response = await api.post('/api/export-all-dxf', formData, {
            responseType: 'blob',
        });
        return response.data;
    },
};

export default apiService;
