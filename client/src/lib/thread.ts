/**
 * Thread API client functions for agent execution
 */

const API_BASE_URL = (import.meta as any)?.env?.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface ThreadInitResponse {
  thread_id: string;
  created_at: string;
  status: string;
}

export interface ThreadExecuteResponse {
  thread_id: string;
  run_id: string;
  status: string;
  created_at: string;
}

/**
 * Initialize a new thread
 */
export async function initiateThread(metadata?: any): Promise<ThreadInitResponse> {
  const response = await fetch(`${API_BASE_URL}/api/agent/initiate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      metadata: metadata || {},
      context: {}
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to initiate thread');
  }

  return response.json();
}

/**
 * Execute a task in a thread
 */
export async function executeThreadTask(
  threadId: string,
  task: string,
  documentId?: string,
  entityId: string = 'default-user'
): Promise<ThreadExecuteResponse> {
  const response = await fetch(`${API_BASE_URL}/api/agent/${threadId}/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      task,
      document_id: documentId,
      entity_id: entityId,
      context_data: [],
      parameters: {}
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to execute task');
  }

  return response.json();
}

/**
 * Get the SSE stream URL for a thread
 */
export function getThreadStreamUrl(threadId: string): string {
  return `${API_BASE_URL}/api/agent/${threadId}/stream`;
}