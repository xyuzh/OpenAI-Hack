/**
 * Composio API client functions
 */

const API_BASE_URL = (import.meta as any)?.env?.VITE_API_BASE_URL ?? "http://localhost:8000";

/**
 * Initiate OAuth authentication for an app
 */
export async function initiateAuth(app: string, entityId: string) {
  const response = await fetch(`${API_BASE_URL}/api/composio/auth/initiate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      app,
      entity_id: entityId,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to initiate authentication');
  }

  return response.json();
}

/**
 * Check connection status for an app
 */
export async function checkConnectionStatus(entityId: string, app: string) {
  const response = await fetch(`${API_BASE_URL}/api/composio/auth/status/${entityId}/${app}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to check connection status');
  }

  return response.json();
}

/**
 * List all connections for a user
 */
export async function listConnections(entityId: string) {
  const response = await fetch(`${API_BASE_URL}/api/composio/auth/connections/${entityId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to list connections');
  }

  return response.json();
}

/**
 * Fetch Google Docs for a user
 */
export async function fetchDocuments(entityId: string, query?: string) {
  const params = new URLSearchParams({
    entity_id: entityId,
  });

  if (query) {
    params.append('query', query);
  }

  const response = await fetch(`${API_BASE_URL}/api/documents?${params}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch documents');
  }

  return response.json();
}

/**
 * Fetch mock documents for testing
 */
export async function fetchMockDocuments() {
  const response = await fetch(`${API_BASE_URL}/api/documents/mock/test-data`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch mock documents');
  }

  return response.json();
}

/**
 * Generate content for a document
 */
export async function generateContent(documentId: string, entityId: string) {
  const params = new URLSearchParams({
    entity_id: entityId,
  });

  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/generate?${params}`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to generate content');
  }

  return response.json();
}

/**
 * Disconnect an app
 */
export async function disconnectApp(entityId: string, app: string) {
  const response = await fetch(`${API_BASE_URL}/api/composio/auth/disconnect/${entityId}/${app}`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to disconnect app');
  }

  return response.json();
}