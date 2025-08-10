<script>
  import { onMount } from 'svelte';
  import FileList from "./components/FileList.svelte";
  import AuthButton from "./components/AuthButton.svelte";
  import ChatUI from "./components/ChatUI.svelte";
  import { fetchDocuments, fetchMockDocuments, checkConnectionStatus } from './lib/composio';

  // User entity ID - in production, this should come from user session/auth
  // Using 'default-user' which already has an active Google Docs connection
  const ENTITY_ID = 'default-user';

  let documents = [];
  let isLoading = true;
  let error = '';
  let isConnected = false;
  let useMockData = false; // Toggle for testing
  
  // Chat UI state
  let showChatUI = false;
  let currentThreadId = '';
  let currentRunId = '';
  let currentDocumentName = '';

  onMount(async () => {
    await checkGoogleDocsConnection();
    await loadDocuments();
  });

  async function checkGoogleDocsConnection() {
    try {
      const status = await checkConnectionStatus(ENTITY_ID, 'googledocs');
      isConnected = status.connected;
    } catch (err) {
      console.error('Failed to check Google Docs connection:', err);
    }
  }

  async function loadDocuments() {
    isLoading = true;
    error = '';
    
    console.log('Loading documents...', { isConnected, useMockData, entityId: ENTITY_ID });

    try {
      if (useMockData) {
        // Use mock data for testing
        console.log('Fetching mock documents...');
        const response = await fetchMockDocuments();
        documents = response.documents || [];
        console.log('Mock documents loaded:', documents.length);
      } else if (isConnected) {
        // Fetch real documents from Google Docs
        console.log('Fetching real Google Docs...');
        const response = await fetchDocuments(ENTITY_ID);
        documents = response.documents || [];
        console.log('Real documents loaded:', documents.length);
      } else {
        // Show sample document when not connected
        documents = [
          {
            "id": "sample-doc-1",
            "name": "Sample Document (Connect Google Docs to see your real documents)",
            "mimeType": "application/vnd.google-apps.document",
            "createdTime": new Date().toISOString(),
            "modifiedTime": new Date().toISOString(),
            "size": "0",
            "starred": false,
            "trashed": false,
            "shared": false,
            "owners": [
              {
                "displayName": "Demo User",
                "emailAddress": "demo@example.com",
                "kind": "drive#user"
              }
            ]
          }
        ];
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load documents';
      console.error('Error loading documents:', err);
      documents = [];
    } finally {
      isLoading = false;
    }
  }

  function handleGoogleDocsConnected() {
    console.log('Google Docs connected! Updating state and loading documents...');
    isConnected = true;
    loadDocuments(); // Reload documents after connection
  }

  function handleDocumentOpen(doc) {
    console.log('Opening document:', doc);
    // Implement document opening logic here
    if (doc.webViewLink) {
      window.open(doc.webViewLink, '_blank');
    }
  }

  function handleStartChat(event) {
    console.log('Starting chat UI:', event.detail);
    currentThreadId = event.detail.threadId;
    currentRunId = event.detail.runId;
    currentDocumentName = event.detail.documentName || 'Document';
    showChatUI = true;
  }

  function handleCloseChat() {
    console.log('Closing chat UI');
    showChatUI = false;
    currentThreadId = '';
    currentRunId = '';
    currentDocumentName = '';
  }
</script>

<div class="app">
  <!-- Header with auth buttons -->
  <header class="header">
    <h1>Document Manager</h1>
    <div class="auth-controls">
      <AuthButton 
        app="googledocs" 
        entityId={ENTITY_ID} 
        onConnected={handleGoogleDocsConnected} 
      />
      <AuthButton 
        app="gmail" 
        entityId={ENTITY_ID} 
      />
      <AuthButton 
        app="jira" 
        entityId={ENTITY_ID} 
      />
    </div>
  </header>

  <!-- Debug controls (remove in production) -->
  <div class="debug-controls">
    <label>
      <input 
        type="checkbox" 
        bind:checked={useMockData}
        on:change={loadDocuments}
      />
      Use mock data
    </label>
    <button on:click={loadDocuments}>Refresh</button>
  </div>

  <!-- Main content -->
  <main class="main">
    {#if showChatUI}
      <ChatUI 
        threadId={currentThreadId}
        runId={currentRunId}
        documentName={currentDocumentName}
        onClose={handleCloseChat}
      />
    {:else if isLoading}
      <div class="loading">Loading documents...</div>
    {:else if error}
      <div class="error">
        <p>Error: {error}</p>
        <button on:click={loadDocuments}>Retry</button>
      </div>
    {:else if !isConnected && !useMockData}
      <div class="connection-prompt">
        <h2>Welcome to Document Manager</h2>
        <p>Connect your Google Docs account to get started</p>
        <div class="prompt-button">
          <AuthButton 
            app="googledocs" 
            entityId={ENTITY_ID} 
            onConnected={handleGoogleDocsConnected} 
          />
        </div>
      </div>
    {:else}
      <FileList 
        documents={documents} 
        onOpen={handleDocumentOpen}
        on:startChat={handleStartChat}
        entityId={ENTITY_ID}
      />
    {/if}
  </main>
</div>

<style>
  .app {
    min-height: 100vh;
    background: #f9fafb;
  }

  .header {
    background: white;
    border-bottom: 1px solid #e5e7eb;
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .header h1 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: #111827;
  }

  .auth-controls {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .debug-controls {
    padding: 1rem 2rem;
    background: #fef3c7;
    border-bottom: 1px solid #fde68a;
    display: flex;
    gap: 1rem;
    align-items: center;
    font-size: 0.875rem;
  }

  .debug-controls label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .debug-controls button {
    padding: 0.25rem 0.75rem;
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    cursor: pointer;
  }

  .debug-controls button:hover {
    background: #f3f4f6;
  }

  .main {
    padding: 2rem;
    max-width: 1400px;
    margin: 0 auto;
  }

  .loading {
    text-align: center;
    padding: 3rem;
    color: #6b7280;
  }

  .error {
    text-align: center;
    padding: 3rem;
    color: #dc2626;
  }

  .error button {
    margin-top: 1rem;
    padding: 0.5rem 1rem;
    background: #dc2626;
    color: white;
    border: none;
    border-radius: 0.5rem;
    cursor: pointer;
  }

  .error button:hover {
    background: #b91c1c;
  }

  .connection-prompt {
    text-align: center;
    padding: 4rem 2rem;
    background: white;
    border-radius: 1rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .connection-prompt h2 {
    margin: 0 0 1rem 0;
    font-size: 1.875rem;
    font-weight: 600;
    color: #111827;
  }

  .connection-prompt p {
    margin: 0 0 2rem 0;
    color: #6b7280;
    font-size: 1.125rem;
  }

  .prompt-button {
    display: flex;
    justify-content: center;
  }
</style>