// ExportPanel Component - Export buttons for DXF download
import React from 'react';
import { Download, Package } from 'lucide-react';

interface ExportPanelProps {
    hasLayouts: boolean;
    onExportAll: () => void;
    loading: boolean;
}

export const ExportPanel: React.FC<ExportPanelProps> = ({
    hasLayouts,
    onExportAll,
    loading,
}) => {
    if (!hasLayouts) {
        return null;
    }

    return (
        <div className="export-panel">
            <button
                className="btn btn-primary btn-export-all"
                onClick={onExportAll}
                disabled={loading}
            >
                <Package size={18} />
                Export All as ZIP
                <Download size={16} />
            </button>
        </div>
    );
};

export default ExportPanel;
