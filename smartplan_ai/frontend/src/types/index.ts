// Types for SmartPlan AI

export interface Feature {
    type: 'Feature';
    geometry: {
        type: 'Polygon' | 'LineString';
        coordinates: number[][] | number[][][];
    };
    properties: {
        type: 'boundary' | 'road' | 'block' | 'lot' | 'green_space';
        index: number;
        name: string;
        area?: number;
        length?: number;
        width?: number;
    };
}

export interface FeatureCollection {
    type: 'FeatureCollection';
    features: Feature[];
}

export interface DesignState {
    boundary: Feature | null;
    designState: FeatureCollection | null;
    currentTemplate: string | null;
    selectedElement: SelectedElement | null;  // Primary selection
    selectedElements: SelectedElement[];      // Multi-selection array
}

export interface SelectedElement {
    name: string;
    type: string;
    index: number;
}

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

export interface ActionResult {
    success: boolean;
    message: string;
    road_count?: number;
    block_count?: number;
    lot_count?: number;
}

export interface ChatResponse {
    text: string;
    action: object | null;
    action_result: ActionResult | null;
    state: FeatureCollection;
}

export interface Template {
    name: string;
    display_name: string;
    description: string;
    icon: string;
}
