'use client';

import React, { useRef, useEffect, useMemo } from 'react';
import { BlockInfo, AssetInfo, InfrastructureLine } from '@/types/api';

interface MapCanvasProps {
    boundary: number[][] | null;
    blocks: BlockInfo[];
    infrastructure?: {
        electric_lines: InfrastructureLine[];
        water_lines: InfrastructureLine[];
    };
    selectedBlockId?: string;
    onBlockClick?: (block: BlockInfo) => void;
    width?: number;
    height?: number;
}

// Color palette
const COLORS = {
    boundary: '#3b82f6',
    block: '#22c55e',
    blockSelected: '#eab308',
    road: '#6b7280',
    factory_standard: '#ef4444',
    warehouse_cold: '#3b82f6',
    office_hq: '#8b5cf6',
    parking_lot: '#6b7280',
    green_buffer: '#22c55e',
    utility_station: '#f97316',
    internal_road: '#4b5563', // Gray-600
    electric: '#eab308',
    water: '#06b6d4',
};

export default function MapCanvas({
    boundary,
    blocks,
    infrastructure,
    selectedBlockId,
    onBlockClick,
    width = 800,
    height = 600,
}: MapCanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    // Calculate bounds and scale
    const { scale, offsetX, offsetY, bounds } = useMemo(() => {
        if (!boundary || boundary.length === 0) {
            return { scale: 1, offsetX: 0, offsetY: 0, bounds: null };
        }

        const xs = boundary.map(c => c[0]);
        const ys = boundary.map(c => c[1]);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);

        const boundsWidth = maxX - minX;
        const boundsHeight = maxY - minY;

        const padding = 40;
        const availableWidth = width - padding * 2;
        const availableHeight = height - padding * 2;

        const scaleX = availableWidth / boundsWidth;
        const scaleY = availableHeight / boundsHeight;
        const scale = Math.min(scaleX, scaleY);

        const offsetX = padding + (availableWidth - boundsWidth * scale) / 2 - minX * scale;
        const offsetY = padding + (availableHeight - boundsHeight * scale) / 2 - minY * scale;

        return {
            scale,
            offsetX,
            offsetY,
            bounds: { minX, maxX, minY, maxY, width: boundsWidth, height: boundsHeight },
        };
    }, [boundary, width, height]);

    // Transform coordinates
    const transform = (x: number, y: number): [number, number] => {
        return [x * scale + offsetX, height - (y * scale + offsetY)];
    };

    // Draw polygon
    const drawPolygon = (
        ctx: CanvasRenderingContext2D,
        coords: number[][],
        fillColor: string,
        strokeColor: string,
        lineWidth: number = 2
    ) => {
        if (!coords || coords.length < 3) return;

        ctx.beginPath();
        const [startX, startY] = transform(coords[0][0], coords[0][1]);
        ctx.moveTo(startX, startY);

        for (let i = 1; i < coords.length; i++) {
            const [x, y] = transform(coords[i][0], coords[i][1]);
            ctx.lineTo(x, y);
        }
        ctx.closePath();

        if (fillColor) {
            ctx.fillStyle = fillColor;
            ctx.fill();
        }
        if (strokeColor) {
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = lineWidth;
            ctx.stroke();
        }
    };

    // Draw line
    const drawLine = (
        ctx: CanvasRenderingContext2D,
        coords: number[][],
        color: string,
        lineWidth: number = 2,
        dashed: boolean = false
    ) => {
        if (!coords || coords.length < 2) return;

        ctx.beginPath();
        if (dashed) ctx.setLineDash([5, 5]);
        else ctx.setLineDash([]);

        const [startX, startY] = transform(coords[0][0], coords[0][1]);
        ctx.moveTo(startX, startY);

        for (let i = 1; i < coords.length; i++) {
            const [x, y] = transform(coords[i][0], coords[i][1]);
            ctx.lineTo(x, y);
        }

        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.stroke();
        ctx.setLineDash([]);
    };

    // Draw label
    const drawLabel = (
        ctx: CanvasRenderingContext2D,
        text: string,
        coords: number[][],
        color: string = '#fff'
    ) => {
        if (!coords || coords.length < 3) return;

        // Calculate centroid
        let sumX = 0, sumY = 0;
        for (const c of coords) {
            sumX += c[0];
            sumY += c[1];
        }
        const [cx, cy] = transform(sumX / coords.length, sumY / coords.length);

        ctx.font = 'bold 12px Inter, sans-serif';
        ctx.fillStyle = color;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, cx, cy);
    };

    // Main render
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Clear
        ctx.fillStyle = '#1f2937';
        ctx.fillRect(0, 0, width, height);

        // Draw boundary
        if (boundary && boundary.length > 0) {
            drawPolygon(ctx, boundary, 'rgba(59, 130, 246, 0.1)', COLORS.boundary, 3);
        }

        // Draw blocks
        for (const block of blocks) {
            const isSelected = block.id === selectedBlockId;
            const fillColor = isSelected ? 'rgba(234, 179, 8, 0.3)' : 'rgba(34, 197, 94, 0.2)';
            const strokeColor = isSelected ? COLORS.blockSelected : COLORS.block;

            drawPolygon(ctx, block.polygon, fillColor, strokeColor, isSelected ? 3 : 2);
            drawLabel(ctx, block.id, block.polygon, '#fff');

            // Draw assets
            for (const asset of block.assets) {
                const assetColor = COLORS[asset.type as keyof typeof COLORS] || '#888';
                drawPolygon(ctx, asset.polygon, assetColor + '80', assetColor, 1);
            }
        }

        // Draw infrastructure
        if (infrastructure) {
            for (const line of infrastructure.electric_lines) {
                drawLine(ctx, line.coordinates, COLORS.electric, 2, false);
            }
            for (const line of infrastructure.water_lines) {
                drawLine(ctx, line.coordinates, COLORS.water, 2, true);
            }
        }

        // Draw legend
        const legend = [
            { label: 'Boundary', color: COLORS.boundary },
            { label: 'Block', color: COLORS.block },
            { label: 'Electric', color: COLORS.electric },
            { label: 'Water', color: COLORS.water },
        ];

        ctx.font = '11px Inter, sans-serif';
        let ly = 20;
        for (const item of legend) {
            ctx.fillStyle = item.color;
            ctx.fillRect(width - 100, ly - 8, 12, 12);
            ctx.fillStyle = '#fff';
            ctx.textAlign = 'left';
            ctx.fillText(item.label, width - 82, ly);
            ly += 18;
        }

    }, [boundary, blocks, infrastructure, selectedBlockId, scale, offsetX, offsetY, width, height]);

    // Handle click
    const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
        if (!onBlockClick || !blocks.length) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;

        // Check which block was clicked (simplified point-in-polygon)
        for (const block of blocks) {
            const [cx, cy] = transform(
                block.polygon.reduce((s, c) => s + c[0], 0) / block.polygon.length,
                block.polygon.reduce((s, c) => s + c[1], 0) / block.polygon.length
            );

            const dist = Math.sqrt((clickX - cx) ** 2 + (clickY - cy) ** 2);
            if (dist < 50) {
                onBlockClick(block);
                return;
            }
        }
    };

    return (
        <canvas
            ref={canvasRef}
            width={width}
            height={height}
            onClick={handleClick}
            className="rounded-lg border border-gray-700 cursor-pointer"
        />
    );
}
