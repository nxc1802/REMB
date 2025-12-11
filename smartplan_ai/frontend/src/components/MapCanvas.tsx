'use client';

import { useRef, useEffect, useCallback } from 'react';
import { Feature, FeatureCollection, SelectedElement } from '@/types';

interface MapCanvasProps {
    designState: FeatureCollection | null;
    selectedElement: SelectedElement | null;       // Primary selection
    selectedElements: SelectedElement[];           // Multi-selection array
    onSelectElement: (element: SelectedElement | null, isMulti?: boolean) => void;
    showLabels?: boolean;
}

interface TransformFn {
    (x: number, y: number): { x: number; y: number };
}

interface Bounds {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
}

interface FeatureBounds {
    name: string;
    type: string;
    coords: Array<{ x: number; y: number }>;
    isLine?: boolean;
}

export default function MapCanvas({
    designState,
    selectedElement,
    selectedElements = [],
    onSelectElement,
    showLabels = true,
}: MapCanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const featureBoundsRef = useRef<FeatureBounds[]>([]);

    // Calculate bounds from features
    const calculateBounds = useCallback((): Bounds | null => {
        if (!designState?.features?.length) return null;

        let coords: number[][] = [];

        designState.features.forEach((f) => {
            if (f.geometry.type === 'Polygon') {
                coords.push(...(f.geometry.coordinates as number[][][])[0]);
            } else if (f.geometry.type === 'LineString') {
                coords.push(...(f.geometry.coordinates as number[][]));
            }
        });

        if (!coords.length) return null;

        return {
            minX: Math.min(...coords.map((c) => c[0])),
            maxX: Math.max(...coords.map((c) => c[0])),
            minY: Math.min(...coords.map((c) => c[1])),
            maxY: Math.max(...coords.map((c) => c[1])),
        };
    }, [designState]);

    // Get colors for element type
    const getColors = (type: string, isSelected: boolean) => {
        if (isSelected) {
            return { fill: 'rgba(243, 156, 18, 0.4)', stroke: '#f39c12', width: 3 };
        }

        switch (type) {
            case 'boundary':
                return { fill: 'rgba(255,255,255,0.05)', stroke: '#ffffff', width: 2 };
            case 'road':
                return { fill: 'transparent', stroke: '#ef4444', width: 4 };
            case 'block':
                return { fill: 'rgba(99, 102, 241, 0.25)', stroke: '#6366f1', width: 1.5 };
            case 'lot':
                return { fill: 'rgba(34, 197, 94, 0.25)', stroke: '#22c55e', width: 1 };
            case 'green_space':
                return { fill: 'rgba(34, 197, 94, 0.5)', stroke: '#16a34a', width: 1 };
            default:
                return { fill: 'rgba(255,255,255,0.1)', stroke: '#ffffff', width: 1 };
        }
    };

    // Get centroid of polygon
    const getCentroid = (coords: number[][]): [number, number] => {
        const n = coords.length - 1;
        let sumX = 0, sumY = 0;
        for (let i = 0; i < n; i++) {
            sumX += coords[i][0];
            sumY += coords[i][1];
        }
        return [sumX / n, sumY / n];
    };

    // Draw label on canvas
    const drawLabel = (
        ctx: CanvasRenderingContext2D,
        x: number,
        y: number,
        text: string,
        isSelected: boolean = false,
        type: string = ''
    ) => {
        const fontSize = type === 'lot' ? 9 : 11;
        ctx.font = isSelected ? `bold ${fontSize}px Inter, sans-serif` : `${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        // Background
        const metrics = ctx.measureText(text);
        const padding = 3;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.beginPath();
        ctx.roundRect(
            x - metrics.width / 2 - padding,
            y - fontSize / 2 - padding,
            metrics.width + padding * 2,
            fontSize + padding * 2,
            3
        );
        ctx.fill();

        // Text
        ctx.fillStyle = isSelected ? '#f59e0b' : '#ffffff';
        ctx.fillText(text, x, y);
    };

    // Main render function
    const render = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Set canvas size
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);

        // Clear canvas
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(0, 0, rect.width, rect.height);

        if (!designState?.features?.length) {
            // Placeholder
            ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
            ctx.font = '16px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Tải ranh giới để bắt đầu', rect.width / 2, rect.height / 2);
            return;
        }

        // Calculate bounds and transform
        const bounds = calculateBounds();
        if (!bounds) return;

        const padding = 50;
        const scaleX = (rect.width - 2 * padding) / (bounds.maxX - bounds.minX);
        const scaleY = (rect.height - 2 * padding) / (bounds.maxY - bounds.minY);
        const scale = Math.min(scaleX, scaleY);

        const offsetX = padding + (rect.width - 2 * padding - (bounds.maxX - bounds.minX) * scale) / 2;
        const offsetY = padding + (rect.height - 2 * padding - (bounds.maxY - bounds.minY) * scale) / 2;

        const transform: TransformFn = (x: number, y: number) => ({
            x: offsetX + (x - bounds.minX) * scale,
            y: rect.height - (offsetY + (y - bounds.minY) * scale),
        });

        // Reset feature bounds for hit testing
        featureBoundsRef.current = [];

        // Draw features in order
        const order = ['boundary', 'block', 'lot', 'green_space', 'road'];

        order.forEach((type) => {
            designState.features
                .filter((f) => f.properties?.type === type)
                .forEach((feature) => {
                    const props = feature.properties;
                    // Check both single selection and multi-selection
                    const isSelected = selectedElement?.name === props.name ||
                        selectedElements.some(e => e.name === props.name);
                    const colors = getColors(type, isSelected);

                    if (feature.geometry.type === 'Polygon') {
                        const coords = (feature.geometry.coordinates as number[][][])[0];
                        const transformedCoords = coords.map((c) => transform(c[0], c[1]));

                        // Draw polygon
                        ctx.beginPath();
                        ctx.moveTo(transformedCoords[0].x, transformedCoords[0].y);
                        for (let i = 1; i < transformedCoords.length; i++) {
                            ctx.lineTo(transformedCoords[i].x, transformedCoords[i].y);
                        }
                        ctx.closePath();

                        ctx.fillStyle = colors.fill;
                        ctx.fill();
                        ctx.strokeStyle = colors.stroke;
                        ctx.lineWidth = colors.width;
                        ctx.stroke();

                        // Store for hit testing
                        if (props.name) {
                            featureBoundsRef.current.push({
                                name: props.name,
                                type: type,
                                coords: transformedCoords,
                            });
                        }

                        // Draw label
                        if (showLabels && props.name && (type === 'block' || type === 'lot')) {
                            const centroid = getCentroid(coords);
                            const tc = transform(centroid[0], centroid[1]);
                            drawLabel(ctx, tc.x, tc.y, props.name, isSelected, type);
                        }
                    } else if (feature.geometry.type === 'LineString') {
                        const coords = feature.geometry.coordinates as number[][];
                        const transformedCoords = coords.map((c) => transform(c[0], c[1]));

                        // Calculate line width based on road width (scaled to screen)
                        const roadWidth = props.width || 24;
                        const scaledWidth = Math.max(2, roadWidth * scale * 0.3);

                        // Draw line with width reflecting actual road width
                        ctx.beginPath();
                        ctx.moveTo(transformedCoords[0].x, transformedCoords[0].y);
                        for (let i = 1; i < transformedCoords.length; i++) {
                            ctx.lineTo(transformedCoords[i].x, transformedCoords[i].y);
                        }
                        ctx.strokeStyle = isSelected ? '#f59e0b' : colors.stroke;
                        ctx.lineWidth = isSelected ? scaledWidth + 3 : scaledWidth;
                        ctx.lineCap = 'round';
                        ctx.stroke();

                        // Store for hit testing
                        if (props.name) {
                            featureBoundsRef.current.push({
                                name: props.name,
                                type: 'road',
                                coords: transformedCoords,
                                isLine: true,
                            });
                        }

                        // Draw label with width info
                        if (showLabels && props.name) {
                            const midIdx = Math.floor(coords.length / 2);
                            const mid = transform(coords[midIdx][0], coords[midIdx][1]);
                            const label = `${props.name} (${roadWidth}m)`;
                            drawLabel(ctx, mid.x, mid.y - 15, label, isSelected, 'road');
                        }
                    }
                });
        });
    }, [designState, selectedElement, showLabels, calculateBounds]);

    // Hit testing
    const isPointInPolygon = (x: number, y: number, coords: Array<{ x: number; y: number }>) => {
        let inside = false;
        for (let i = 0, j = coords.length - 1; i < coords.length; j = i++) {
            const xi = coords[i].x, yi = coords[i].y;
            const xj = coords[j].x, yj = coords[j].y;
            const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    };

    const isPointNearLine = (x: number, y: number, coords: Array<{ x: number; y: number }>, threshold: number) => {
        for (let i = 0; i < coords.length - 1; i++) {
            const x1 = coords[i].x, y1 = coords[i].y;
            const x2 = coords[i + 1].x, y2 = coords[i + 1].y;

            const A = x - x1, B = y - y1, C = x2 - x1, D = y2 - y1;
            const dot = A * C + B * D;
            const lenSq = C * C + D * D;
            let param = lenSq !== 0 ? dot / lenSq : -1;

            let xx: number, yy: number;
            if (param < 0) { xx = x1; yy = y1; }
            else if (param > 1) { xx = x2; yy = y2; }
            else { xx = x1 + param * C; yy = y1 + param * D; }

            const dx = x - xx, dy = y - yy;
            if (Math.sqrt(dx * dx + dy * dy) < threshold) return true;
        }
        return false;
    };

    const findElementAt = (x: number, y: number): SelectedElement | null => {
        // Check in reverse order (top-most first)
        for (let i = featureBoundsRef.current.length - 1; i >= 0; i--) {
            const f = featureBoundsRef.current[i];
            if (f.isLine) {
                if (isPointNearLine(x, y, f.coords, 12)) {
                    return { name: f.name, type: f.type, index: 0 };
                }
            } else {
                if (isPointInPolygon(x, y, f.coords)) {
                    return { name: f.name, type: f.type, index: 0 };
                }
            }
        }
        return null;
    };

    // Event handlers
    const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const clicked = findElementAt(x, y);
        // Shift+click for multi-selection
        const isMultiSelect = e.shiftKey;
        onSelectElement(clicked, isMultiSelect);
    };

    const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const hovered = findElementAt(x, y);
        canvas.style.cursor = hovered ? 'pointer' : 'default';
    };

    // Re-render when state changes
    useEffect(() => {
        render();
    }, [render]);

    // Handle resize
    useEffect(() => {
        const handleResize = () => render();
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, [render]);

    return (
        <canvas
            ref={canvasRef}
            onClick={handleClick}
            onMouseMove={handleMouseMove}
            className="w-full h-full rounded-lg"
            style={{ background: '#0f172a' }}
        />
    );
}
