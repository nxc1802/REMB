/**
 * AIOptimize™ MVP - Main Application
 * Industrial Estate Planning Optimization
 */
import { useState, useCallback, useEffect } from 'react';
import { Layers, Zap, AlertCircle, Loader2 } from 'lucide-react';
import { FileUploadPanel } from './components/FileUploadPanel';
import { Map2DPlotter } from './components/Map2DPlotter';
import { LayoutOptionsPanel } from './components/LayoutOptionsPanel';
import { ChatInterface } from './components/ChatInterface';
import { ExportPanel } from './components/ExportPanel';
import { apiService } from './services/api';
import type { AppState, ChatMessage, GeoJSONFeature } from './types';
import './App.css';

function App() {
  // Application state
  const [state, setState] = useState<AppState>({
    sessionId: null,
    boundary: null,
    boundaryCoords: null,
    metadata: null,
    options: [],
    selectedOption: null,
    messages: [],
    loading: false,
    error: null,
  });

  // Loading states
  const [uploadLoading, setUploadLoading] = useState(false);
  const [generateLoading, setGenerateLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);

  // Debug: monitor options changes
  useEffect(() => {
    console.log('State options changed:', state.options.length, state.options);
  }, [state.options]);

  // Extract boundary coords from GeoJSON
  const extractCoords = (geojson: GeoJSONFeature): number[][] => {
    if (geojson.type === 'Feature' && geojson.geometry) {
      return geojson.geometry.coordinates[0];
    }
    return [];
  };

  // Handle file upload
  const handleUpload = useCallback(async (file: File) => {
    setUploadLoading(true);
    setState(prev => ({ ...prev, error: null }));

    try {
      const response = await apiService.uploadBoundaryFile(file);
      const coords = extractCoords(response.boundary);

      setState(prev => ({
        ...prev,
        sessionId: response.session_id,
        boundary: response.boundary,
        boundaryCoords: coords,
        metadata: response.metadata,
        options: [],
        selectedOption: null,
      }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Upload failed'
      }));
    } finally {
      setUploadLoading(false);
    }
  }, []);

  // Handle sample data
  const handleSampleData = useCallback(async () => {
    setUploadLoading(true);
    setState(prev => ({ ...prev, error: null }));

    try {
      const sampleData = await apiService.getSampleData();
      const response = await apiService.uploadBoundary(sampleData);
      const coords = extractCoords(response.boundary);

      setState(prev => ({
        ...prev,
        sessionId: response.session_id,
        boundary: response.boundary,
        boundaryCoords: coords,
        metadata: response.metadata,
        options: [],
        selectedOption: null,
      }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Failed to load sample data'
      }));
    } finally {
      setUploadLoading(false);
    }
  }, []);

  // Generate layouts
  const handleGenerate = useCallback(async () => {
    if (!state.sessionId) return;

    setGenerateLoading(true);
    setState(prev => ({ ...prev, error: null }));

    try {
      const response = await apiService.generateLayouts(state.sessionId);
      console.log('Generate response:', response);

      if (response.options && response.options.length > 0) {
        setState(prev => ({
          ...prev,
          options: response.options,
          selectedOption: response.options[0]?.id || null,
        }));
      } else {
        setState(prev => ({
          ...prev,
          error: 'No layout options returned'
        }));
      }
    } catch (err) {
      console.error('Generate error:', err);
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Generation failed'
      }));
    } finally {
      setGenerateLoading(false);
    }
  }, [state.sessionId]);

  // Select layout option
  const handleSelectOption = useCallback((optionId: number) => {
    setState(prev => ({ ...prev, selectedOption: optionId }));
  }, []);

  // Export single DXF
  const handleExportDxf = useCallback(async (optionId: number) => {
    if (!state.sessionId) return;

    setExportLoading(true);

    try {
      const blob = await apiService.exportDxf(state.sessionId, optionId);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `layout_option_${optionId}.dxf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Export failed'
      }));
    } finally {
      setExportLoading(false);
    }
  }, [state.sessionId]);

  // Export all as ZIP
  const handleExportAll = useCallback(async () => {
    if (!state.sessionId) return;

    setExportLoading(true);

    try {
      const blob = await apiService.exportAllDxf(state.sessionId);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'all_layouts.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Export failed'
      }));
    } finally {
      setExportLoading(false);
    }
  }, [state.sessionId]);

  // Send chat message
  const handleChat = useCallback(async (message: string) => {
    if (!state.sessionId) return;

    const userMessage: ChatMessage = { role: 'user', content: message };
    setState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
    }));

    setChatLoading(true);

    try {
      const response = await apiService.chat(state.sessionId, message);

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.message,
        model: response.model,
      };

      setState(prev => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));
    } catch (err) {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        model: 'fallback',
      };
      setState(prev => ({
        ...prev,
        messages: [...prev.messages, errorMessage],
      }));
    } finally {
      setChatLoading(false);
    }
  }, [state.sessionId]);

  // Get selected option object
  const selectedOptionData = state.options.find(o => o.id === state.selectedOption) || null;

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">
          <Layers size={28} />
          <h1>AIOptimize™</h1>
        </div>
        <p className="tagline">AI-Powered Industrial Estate Planning</p>
      </header>

      {state.error && (
        <div className="error-banner">
          <AlertCircle size={18} />
          <span>{state.error}</span>
          <button onClick={() => setState(prev => ({ ...prev, error: null }))}>×</button>
        </div>
      )}

      <main className="app-main">
        <div className="left-panel">
          <FileUploadPanel
            onUpload={handleUpload}
            onSampleData={handleSampleData}
            loading={uploadLoading}
            hasData={!!state.boundary}
          />

          {state.boundary && (
            <div className="generate-section">
              <button
                className="btn btn-primary btn-generate"
                onClick={handleGenerate}
                disabled={generateLoading}
              >
                {generateLoading ? (
                  <>
                    <Loader2 size={18} className="spin" />
                    Optimizing...
                  </>
                ) : (
                  <>
                    <Zap size={18} />
                    Generate Layouts
                  </>
                )}
              </button>
            </div>
          )}

          <div className="map-section">
            <Map2DPlotter
              boundaryCoords={state.boundaryCoords}
              metadata={state.metadata}
              selectedOption={selectedOptionData}
              width={720}
              height={500}
            />
          </div>

          <LayoutOptionsPanel
            options={state.options}
            selectedOptionId={state.selectedOption}
            onSelect={handleSelectOption}
            onExport={handleExportDxf}
            loading={exportLoading}
          />

          <ExportPanel
            hasLayouts={state.options.length > 0}
            onExportAll={handleExportAll}
            loading={exportLoading}
          />
        </div>

        <div className="right-panel">
          <ChatInterface
            messages={state.messages}
            onSendMessage={handleChat}
            loading={chatLoading}
            disabled={!state.sessionId}
          />
        </div>
      </main>

      <footer className="app-footer">
        <p>AIOptimize™ MVP • Built with React + FastAPI + Genetic Algorithm</p>
      </footer>
    </div>
  );
}

export default App;
