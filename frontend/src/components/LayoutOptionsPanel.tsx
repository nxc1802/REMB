// LayoutOptionsPanel - Display 3 layout options with metrics
import React from 'react';
import { Download, Check } from 'lucide-react';
import type { LayoutOption } from '../types';

interface LayoutOptionsPanelProps {
    options: LayoutOption[];
    selectedOptionId: number | null;
    onSelect: (optionId: number) => void;
    onExport: (optionId: number) => void;
    loading: boolean;
}

export const LayoutOptionsPanel: React.FC<LayoutOptionsPanelProps> = ({
    options,
    selectedOptionId,
    onSelect,
    onExport,
    loading,
}) => {
    if (options.length === 0) {
        return (
            <div className="options-panel empty">
                <p>Generate layouts to see optimization options</p>
            </div>
        );
    }

    return (
        <div className="options-panel">
            <h3>Layout Options</h3>
            <div className="options-grid">
                {options.map((option) => (
                    <div
                        key={option.id}
                        className={`option-card ${selectedOptionId === option.id ? 'selected' : ''}`}
                        onClick={() => onSelect(option.id)}
                    >
                        <div className="option-header">
                            <span className="option-icon">{option.icon}</span>
                            <h4>{option.name}</h4>
                            {selectedOptionId === option.id && (
                                <Check size={18} className="selected-check" />
                            )}
                        </div>

                        <p className="option-description">{option.description}</p>

                        <div className="option-metrics">
                            <div className="metric">
                                <span className="metric-label">Plots</span>
                                <span className="metric-value">{option.metrics.total_plots}</span>
                            </div>
                            <div className="metric">
                                <span className="metric-label">Total Area</span>
                                <span className="metric-value">{option.metrics.total_area.toLocaleString()} m²</span>
                            </div>
                            <div className="metric">
                                <span className="metric-label">Avg Size</span>
                                <span className="metric-value">{Math.round(option.metrics.avg_size).toLocaleString()} m²</span>
                            </div>
                            <div className="metric">
                                <span className="metric-label">Fitness</span>
                                <span className="metric-value fitness">{(option.metrics.fitness * 100).toFixed(0)}%</span>
                            </div>
                        </div>

                        <div className="option-footer">
                            <span className={`compliance ${option.metrics.compliance === 'PASS' ? 'pass' : 'fail'}`}>
                                {option.metrics.compliance === 'PASS' ? '✓ Compliant' : '✗ Issues'}
                            </span>
                            <button
                                className="btn btn-sm btn-export"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onExport(option.id);
                                }}
                                disabled={loading}
                            >
                                <Download size={14} />
                                DXF
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default LayoutOptionsPanel;
