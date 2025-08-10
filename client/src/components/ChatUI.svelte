<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { createEventDispatcher } from 'svelte';

  export let threadId: string;
  export let runId: string;
  export let documentName: string = '';
  export let onClose: () => void = () => {};

  const dispatch = createEventDispatcher();

  interface Message {
    id: string;
    type: 'user' | 'agent' | 'status' | 'tool' | 'error';
    content: string;
    timestamp: string;
    metadata?: any;
  }

  let messages: Message[] = [];
  let isConnected = false;
  let isLoading = true;
  let error: string | null = null;
  let eventSource: EventSource | null = null;
  let messageContainer: HTMLDivElement;

  const API_BASE_URL = (import.meta as any)?.env?.VITE_API_BASE_URL ?? "http://localhost:8000";

  onMount(() => {
    connectToStream();
  });

  onDestroy(() => {
    disconnectStream();
  });

  function connectToStream() {
    if (eventSource) {
      disconnectStream();
    }

    isLoading = true;
    error = null;

    const streamUrl = `${API_BASE_URL}/api/agent/${threadId}/stream`;
    console.log('Connecting to SSE stream:', streamUrl);

    eventSource = new EventSource(streamUrl);

    eventSource.onopen = () => {
      console.log('SSE connection opened');
      isConnected = true;
      isLoading = false;
      
      // Add initial message
      addMessage({
        type: 'status',
        content: `Processing document: ${documentName}`,
        timestamp: new Date().toISOString()
      });
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Received SSE message:', data);
        handleStreamMessage(data);
      } catch (err) {
        console.error('Failed to parse SSE message:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE error:', err);
      isConnected = false;
      isLoading = false;
      
      if (eventSource?.readyState === EventSource.CLOSED) {
        error = 'Connection closed. Stream ended.';
        disconnectStream();
      } else {
        error = 'Connection error. Retrying...';
        // Retry connection after delay
        setTimeout(() => {
          if (eventSource?.readyState !== EventSource.OPEN) {
            connectToStream();
          }
        }, 3000);
      }
    };
  }

  function disconnectStream() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
      isConnected = false;
    }
  }

  function handleStreamMessage(data: any) {
    // Handle different message types from the agent
    switch (data.type) {
      case 'message':
        addMessage({
          type: 'agent',
          content: data.content || data.message || '',
          timestamp: data.timestamp || new Date().toISOString(),
          metadata: data.metadata
        });
        break;

      case 'tool_use':
        // Handle tool usage messages
        if (data.tool_name === 'JiraTool' && data.action === 'create_issue') {
          addMessage({
            type: 'tool',
            content: `Creating Jira ticket: ${data.parameters?.title || 'New Issue'}`,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data
          });
        } else if (data.tool_name === 'GoogleDocsTool' && data.action === 'fetch_document') {
          addMessage({
            type: 'tool',
            content: `Fetching Google Doc content...`,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data
          });
        } else {
          addMessage({
            type: 'tool',
            content: `Using tool: ${data.tool_name} - ${data.action || 'processing'}`,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data
          });
        }
        break;

      case 'tool_result':
        // Handle tool results
        if (data.tool_name === 'JiraTool' && data.success) {
          const result = data.result || {};
          const issueKey = result.key || result.issue_key || 'ISSUE-XXX';
          const issueUrl = result.url || result.issue_url || '#';
          addMessage({
            type: 'agent',
            content: `✅ Created Jira ticket: <a href="${issueUrl}" target="_blank" class="jira-link">${issueKey}</a> - ${result.title || 'New Issue'}`,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data
          });
        } else if (data.tool_name === 'GoogleDocsTool' && data.success) {
          addMessage({
            type: 'agent',
            content: `✅ Successfully fetched document content`,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data
          });
        }
        break;

      case 'status':
        // Handle status updates
        if (data.status === 'completed') {
          addMessage({
            type: 'status',
            content: '✅ Task completed successfully!',
            timestamp: data.timestamp || new Date().toISOString()
          });
          disconnectStream();
        } else if (data.status === 'failed' || data.status === 'error') {
          addMessage({
            type: 'error',
            content: `❌ Task failed: ${data.message || 'Unknown error'}`,
            timestamp: data.timestamp || new Date().toISOString()
          });
          disconnectStream();
        } else if (data.status === 'stopped') {
          addMessage({
            type: 'status',
            content: '⏹ Task stopped',
            timestamp: data.timestamp || new Date().toISOString()
          });
          disconnectStream();
        }
        break;

      case 'keep_alive':
        // Ignore keep-alive messages
        break;

      default:
        // Handle any other message types
        if (data.content || data.message) {
          addMessage({
            type: 'agent',
            content: data.content || data.message,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data
          });
        }
    }
  }

  function addMessage(msg: Partial<Message>) {
    const message: Message = {
      id: `msg-${Date.now()}-${Math.random()}`,
      type: msg.type || 'agent',
      content: msg.content || '',
      timestamp: msg.timestamp || new Date().toISOString(),
      metadata: msg.metadata
    };
    
    messages = [...messages, message];
    
    // Scroll to bottom after adding message
    setTimeout(() => {
      if (messageContainer) {
        messageContainer.scrollTop = messageContainer.scrollHeight;
      }
    }, 10);
  }

  function formatTimestamp(timestamp: string): string {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return '';
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      onClose();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="chat-container">
  <div class="chat-header">
    <div class="header-info">
      <h2>Agent Processing</h2>
      <p class="document-name">{documentName}</p>
    </div>
    <div class="header-actions">
      <div class="connection-status" class:connected={isConnected}>
        <span class="status-dot"></span>
        {isConnected ? 'Connected' : 'Disconnected'}
      </div>
      <button class="close-button" on:click={onClose}>
        ✕
      </button>
    </div>
  </div>

  <div class="messages-container" bind:this={messageContainer}>
    {#if isLoading}
      <div class="loading">
        <div class="spinner"></div>
        <p>Connecting to agent...</p>
      </div>
    {/if}

    {#if error}
      <div class="error-message">
        <p>{error}</p>
      </div>
    {/if}

    {#each messages as message (message.id)}
      <div class="message {message.type}">
        <div class="message-header">
          <span class="message-type">
            {#if message.type === 'user'}
              👤 You
            {:else if message.type === 'agent'}
              🤖 Agent
            {:else if message.type === 'tool'}
              🔧 Tool
            {:else if message.type === 'status'}
              ℹ️ Status
            {:else if message.type === 'error'}
              ❌ Error
            {/if}
          </span>
          <span class="message-time">{formatTimestamp(message.timestamp)}</span>
        </div>
        <div class="message-content">
          {@html message.content}
        </div>
      </div>
    {/each}

    {#if messages.length === 0 && !isLoading}
      <div class="no-messages">
        <p>Waiting for agent responses...</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .chat-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: #f9fafb;
  }

  .chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    background: white;
    border-bottom: 1px solid #e5e7eb;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }

  .header-info h2 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #111827;
  }

  .document-name {
    margin: 0.25rem 0 0 0;
    font-size: 0.875rem;
    color: #6b7280;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.75rem;
    background: #fee2e2;
    color: #991b1b;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    font-weight: 500;
  }

  .connection-status.connected {
    background: #dcfce7;
    color: #166534;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .close-button {
    padding: 0.5rem;
    background: transparent;
    border: none;
    color: #6b7280;
    font-size: 1.25rem;
    cursor: pointer;
    border-radius: 0.375rem;
    transition: all 0.2s;
  }

  .close-button:hover {
    background: #f3f4f6;
    color: #111827;
  }

  .messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    color: #6b7280;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #e5e7eb;
    border-top-color: #6366f1;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .loading p {
    margin-top: 1rem;
    font-size: 0.875rem;
  }

  .error-message {
    padding: 1rem;
    background: #fee2e2;
    border: 1px solid #fecaca;
    border-radius: 0.5rem;
    color: #991b1b;
  }

  .message {
    background: white;
    border-radius: 0.75rem;
    padding: 1rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    animation: slideIn 0.3s ease-out;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .message.tool {
    background: #f0f9ff;
    border-left: 3px solid #3b82f6;
  }

  .message.status {
    background: #fefce8;
    border-left: 3px solid #facc15;
  }

  .message.error {
    background: #fee2e2;
    border-left: 3px solid #dc2626;
  }

  .message-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .message-type {
    font-weight: 600;
    font-size: 0.875rem;
    color: #374151;
  }

  .message-time {
    font-size: 0.75rem;
    color: #9ca3af;
  }

  .message-content {
    color: #4b5563;
    line-height: 1.5;
  }

  .message-content :global(.jira-link) {
    color: #2563eb;
    text-decoration: none;
    font-weight: 500;
    border-bottom: 1px solid #93c5fd;
  }

  .message-content :global(.jira-link:hover) {
    color: #1d4ed8;
    border-bottom-color: #60a5fa;
  }

  .no-messages {
    text-align: center;
    padding: 3rem;
    color: #9ca3af;
  }
</style>