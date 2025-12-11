const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';

export async function callAPI<T>(
    endpoint: string,
    method: 'GET' | 'POST' = 'GET',
    data?: object
): Promise<T | null> {
    try {
        const options: RequestInit = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };

        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }

        const url = method === 'GET' && data
            ? `${API_URL}/api/${endpoint}?${new URLSearchParams(data as Record<string, string>)}`
            : `${API_URL}/api/${endpoint}`;

        const response = await fetch(url, options);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return null;
    }
}

export async function setBoundary(boundary: object, sessionId: string) {
    return callAPI('set-boundary', 'POST', { boundary, session_id: sessionId });
}

export async function applyTemplate(
    templateName: string,
    cellSize: number,
    rotation: number,
    sessionId: string
) {
    return callAPI('apply-template', 'POST', {
        template_name: templateName,
        cell_size: cellSize,
        rotation,
        session_id: sessionId,
    });
}

export async function subdivideBlocks(lotSize: number, sessionId: string) {
    return callAPI('subdivide', 'POST', { lot_size: lotSize, session_id: sessionId });
}

export async function sendChatMessage(
    message: string,
    sessionId: string,
    selectedElement?: { name: string; type: string; index: number } | null
) {
    return callAPI('chat', 'POST', {
        message,
        session_id: sessionId,
        selected_element: selectedElement,
    });
}

export async function uploadDXF(file: File) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_URL}/api/upload-dxf`, {
        method: 'POST',
        body: formData,
    });

    return response.json();
}
