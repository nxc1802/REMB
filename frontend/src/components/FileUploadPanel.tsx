// FileUploadPanel Component
import React, { useRef } from 'react';
import { Upload, FileJson, Zap } from 'lucide-react';

interface FileUploadPanelProps {
    onUpload: (file: File) => void;
    onSampleData: () => void;
    loading: boolean;
    hasData: boolean;
}

export const FileUploadPanel: React.FC<FileUploadPanelProps> = ({
    onUpload,
    onSampleData,
    loading,
    hasData,
}) => {
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            onUpload(file);
        }
    };

    const handleClick = () => {
        fileInputRef.current?.click();
    };

    return (
        <div className="upload-panel">
            <div className="upload-header">
                <FileJson size={24} />
                <h3>Site Boundary</h3>
            </div>

            <div className="upload-buttons">
                <button
                    className="btn btn-primary"
                    onClick={handleClick}
                    disabled={loading}
                >
                    <Upload size={18} />
                    {hasData ? 'Replace Boundary' : 'Upload DXF / DWG / GeoJSON'}
                </button>

                <button
                    className="btn btn-secondary"
                    onClick={onSampleData}
                    disabled={loading}
                >
                    <Zap size={18} />
                    Use Sample Data
                </button>
            </div>

            <input
                ref={fileInputRef}
                type="file"
                accept=".dxf,.dwg,.geojson,.json"
                onChange={handleFileChange}
                style={{ display: 'none' }}
            />

            {hasData && (
                <div className="upload-status">
                    ✅ Boundary loaded
                </div>
            )}
        </div>
    );
};

export default FileUploadPanel;
