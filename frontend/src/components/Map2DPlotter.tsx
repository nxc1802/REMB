// Map2DPlotter Component - Konva.js canvas with zoom/pan for site visualization
import React, { useMemo, useState, useRef, useCallback } from 'react';
import { Stage, Layer, Line, Rect, Text, Group } from 'react-konva';
import { ZoomIn, ZoomOut, Move, Maximize2 } from 'lucide-react';
import type { LayoutOption, SiteMetadata } from '../types';
import type Konva from 'konva';

interface Map2DPlotterProps {
    boundaryCoords: number[][] | null;
    metadata: SiteMetadata | null;
    selectedOption: LayoutOption | null;
    width?: number;
    height?: number;
}

export const Map2DPlotter: React.FC<Map2DPlotterProps> = ({
    boundaryCoords,
    metadata,
    selectedOption,
    width = 800,
    height = 600,
}) => {
    // Zoom and pan state
    const [scale, setScale] = useState(1);
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const stageRef = useRef<Konva.Stage>(null);

    // Calculate base transform to fit boundary in canvas
    const baseTransform = useMemo(() => {
        if (!boundaryCoords || boundaryCoords.length === 0) {
            return { scale: 1, offsetX: 0, offsetY: 0, minX: 0, minY: 0 };
        }

        const xs = boundaryCoords.map(c => c[0]);
        const ys = boundaryCoords.map(c => c[1]);

        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);

        const dataWidth = maxX - minX;
        const dataHeight = maxY - minY;

        const padding = 60;
        const scaleX = (width - padding * 2) / dataWidth;
        const scaleY = (height - padding * 2) / dataHeight;
        const baseScale = Math.min(scaleX, scaleY) * 0.85;

        const offsetX = padding + (width - padding * 2 - dataWidth * baseScale) / 2 - minX * baseScale;
        const offsetY = padding + (height - padding * 2 - dataHeight * baseScale) / 2 + maxY * baseScale;

        return { scale: baseScale, offsetX, offsetY, minX, minY, maxY };
    }, [boundaryCoords, width, height]);

    // Transform coordinates (flip Y for screen coords)
    const transformPoint = useCallback((x: number, y: number): [number, number] => {
        return [
            x * baseTransform.scale + baseTransform.offsetX,
            baseTransform.offsetY - y * baseTransform.scale,
        ];
    }, [baseTransform]);

    // Flatten boundary coords for Konva Line
    const boundaryPoints = useMemo(() => {
        if (!boundaryCoords) return [];
        return boundaryCoords.flatMap(([x, y]) => transformPoint(x, y));
    }, [boundaryCoords, transformPoint]);

    // Calculate setback boundary (50m inside)
    const setbackPoints = useMemo(() => {
        if (!boundaryCoords || boundaryCoords.length < 3) return [];

        const xs = boundaryCoords.map(c => c[0]);
        const ys = boundaryCoords.map(c => c[1]);
        const centerX = xs.reduce((a, b) => a + b, 0) / xs.length;
        const centerY = ys.reduce((a, b) => a + b, 0) / ys.length;

        const shrinkFactor = 0.82;
        const shrunkCoords = boundaryCoords.map(([x, y]) => [
            centerX + (x - centerX) * shrinkFactor,
            centerY + (y - centerY) * shrinkFactor,
        ]);

        return shrunkCoords.flatMap(([x, y]) => transformPoint(x, y));
    }, [boundaryCoords, transformPoint]);

    // Handle zoom
    const handleZoom = (delta: number) => {
        const newScale = Math.min(Math.max(scale + delta, 0.5), 3);
        setScale(newScale);
    };

    // Handle wheel zoom
    const handleWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
        e.evt.preventDefault();
        const delta = e.evt.deltaY > 0 ? -0.1 : 0.1;
        handleZoom(delta);
    };

    // Reset view
    const resetView = () => {
        setScale(1);
        setPosition({ x: 0, y: 0 });
    };

    // Render plots from selected option
    const renderPlots = () => {
        if (!selectedOption?.plots) return null;

        return selectedOption.plots.map((plot, index) => {
            // Transform plot position
            const [x, y] = transformPoint(plot.x, plot.y + plot.height);
            const w = plot.width * baseTransform.scale;
            const h = plot.height * baseTransform.scale;

            // Color based on index
            const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];
            const color = colors[index % colors.length];

            return (
                <Group key={index}>
                    <Rect
                        x={x}
                        y={y}
                        width={w}
                        height={h}
                        fill={`${color}33`}
                        stroke={color}
                        strokeWidth={2}
                        cornerRadius={2}
                    />
                    <Text
                        x={x + w / 2 - 12}
                        y={y + h / 2 - 10}
                        text={`P${index + 1}`}
                        fontSize={14}
                        fill={color}
                        fontStyle="bold"
                    />
                    <Text
                        x={x + w / 2 - 25}
                        y={y + h / 2 + 6}
                        text={`${Math.round(plot.area)}m²`}
                        fontSize={10}
                        fill="#666"
                    />
                </Group>
            );
        });
    };

    return (
        <div className="map-wrapper">
            {/* Zoom controls */}
            <div className="map-controls">
                <button onClick={() => handleZoom(0.2)} title="Zoom In">
                    <ZoomIn size={16} />
                </button>
                <button onClick={() => handleZoom(-0.2)} title="Zoom Out">
                    <ZoomOut size={16} />
                </button>
                <button onClick={resetView} title="Reset View">
                    <Maximize2 size={16} />
                </button>
                <span className="zoom-level">{Math.round(scale * 100)}%</span>
            </div>

            <div className="map-container">
                <Stage
                    ref={stageRef}
                    width={width}
                    height={height}
                    scaleX={scale}
                    scaleY={scale}
                    x={position.x}
                    y={position.y}
                    draggable
                    onWheel={handleWheel}
                    onDragEnd={(e) => setPosition({ x: e.target.x(), y: e.target.y() })}
                >
                    <Layer>
                        {/* Background grid */}
                        {[...Array(25)].map((_, i) => (
                            <Line
                                key={`grid-h-${i}`}
                                points={[0, i * (height / 25), width, i * (height / 25)]}
                                stroke="#f0f0f0"
                                strokeWidth={1}
                            />
                        ))}
                        {[...Array(25)].map((_, i) => (
                            <Line
                                key={`grid-v-${i}`}
                                points={[i * (width / 25), 0, i * (width / 25), height]}
                                stroke="#f0f0f0"
                                strokeWidth={1}
                            />
                        ))}

                        {/* Site boundary */}
                        {boundaryPoints.length > 0 && (
                            <Line
                                points={boundaryPoints}
                                closed
                                stroke="#1e293b"
                                strokeWidth={3}
                                fill="rgba(226, 232, 240, 0.3)"
                            />
                        )}

                        {/* Setback zone */}
                        {setbackPoints.length > 0 && (
                            <Line
                                points={setbackPoints}
                                closed
                                stroke="#ef4444"
                                strokeWidth={2}
                                dash={[10, 5]}
                                fill="rgba(239, 68, 68, 0.05)"
                            />
                        )}

                        {/* Plots */}
                        {renderPlots()}

                        {/* Legend */}
                        <Group x={10} y={10}>
                            <Rect x={0} y={0} width={170} height={90} fill="white" opacity={0.95} cornerRadius={8} shadowBlur={5} shadowColor="rgba(0,0,0,0.1)" />
                            <Text x={10} y={8} text="Legend" fontSize={12} fontStyle="bold" fill="#333" />
                            <Line points={[10, 30, 35, 30]} stroke="#1e293b" strokeWidth={3} />
                            <Text x={45} y={24} text="Site Boundary" fontSize={11} fill="#666" />
                            <Line points={[10, 50, 35, 50]} stroke="#ef4444" strokeWidth={2} dash={[5, 3]} />
                            <Text x={45} y={44} text="Setback (50m)" fontSize={11} fill="#666" />
                            <Rect x={10} y={62} width={25} height={18} fill="rgba(59, 130, 246, 0.2)" stroke="#3B82F6" strokeWidth={2} />
                            <Text x={45} y={66} text="Industrial Plots" fontSize={11} fill="#666" />
                        </Group>

                        {/* Metadata */}
                        {metadata && (
                            <Group x={width - 160} y={10}>
                                <Rect x={0} y={0} width={150} height={60} fill="white" opacity={0.95} cornerRadius={8} shadowBlur={5} shadowColor="rgba(0,0,0,0.1)" />
                                <Text x={10} y={8} text="Site Info" fontSize={12} fontStyle="bold" fill="#333" />
                                <Text x={10} y={26} text={`Area: ${(metadata.area / 10000).toFixed(2)} ha`} fontSize={11} fill="#666" />
                                <Text x={10} y={42} text={`Perimeter: ${metadata.perimeter.toFixed(0)} m`} fontSize={11} fill="#666" />
                            </Group>
                        )}

                        {/* Empty state */}
                        {!boundaryCoords && (
                            <Group>
                                <Rect x={width / 2 - 120} y={height / 2 - 30} width={240} height={60} fill="#f8fafc" cornerRadius={8} />
                                <Text
                                    x={width / 2 - 100}
                                    y={height / 2 - 10}
                                    text="Upload DXF or GeoJSON to start"
                                    fontSize={14}
                                    fill="#94a3b8"
                                />
                            </Group>
                        )}
                    </Layer>
                </Stage>
            </div>

            {/* Drag hint */}
            <div className="map-hint">
                <Move size={12} /> Drag to pan • Scroll to zoom
            </div>
        </div>
    );
};

export default Map2DPlotter;
