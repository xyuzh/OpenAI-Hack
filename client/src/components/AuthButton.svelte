<script lang="ts">
  import { onMount } from 'svelte';
  import { initiateAuth, checkConnectionStatus } from '../lib/composio';

  export let app: 'googledocs' | 'gmail' | 'jira';
  export let entityId: string = 'default-user'; // Using consistent entity ID
  export let onConnected: () => void = () => {};

  let isConnected = false;
  let isConnecting = false;
  let error = '';

  // App display names
  const appNames = {
    googledocs: 'Google Docs',
    gmail: 'Gmail',
    jira: 'Jira'
  };

  // App icons (using emojis for simplicity, replace with actual icons)
  const appIcons = {
    googledocs: '📝',
    gmail: '📧',
    jira: '🎯'
  };

  onMount(async () => {
    await checkStatus();
  });

  async function checkStatus() {
    try {
      const status = await checkConnectionStatus(entityId, app);
      console.log(`[${app}] Connection status:`, status);
      isConnected = status.connected;
      if (isConnected) {
        console.log(`[${app}] Connected! Calling onConnected callback`);
        onConnected();
      }
    } catch (err) {
      console.error(`[${app}] Failed to check connection status:`, err);
    }
  }

  async function handleConnect() {
    if (isConnecting || isConnected) return;

    isConnecting = true;
    error = '';

    try {
      // Initiate OAuth flow
      const result = await initiateAuth(app, entityId);
      
      // Open OAuth URL in new window
      const authWindow = window.open(
        result.redirect_url,
        `${app}_auth`,
        'width=600,height=700'
      );

      // Poll for connection status
      let pollCount = 0;
      const maxPolls = 150; // 5 minutes with 2 second intervals
      
      const pollInterval = setInterval(async () => {
        pollCount++;
        console.log(`[${app}] Polling status... (${pollCount}/${maxPolls})`);
        
        try {
          const status = await checkConnectionStatus(entityId, app);
          console.log(`[${app}] Poll result:`, status);
          
          if (status.connected) {
            console.log(`[${app}] Connection successful!`);
            clearInterval(pollInterval);
            isConnected = true;
            isConnecting = false;
            if (authWindow && !authWindow.closed) {
              authWindow.close();
            }
            onConnected();
          } else if (pollCount >= maxPolls) {
            clearInterval(pollInterval);
            isConnecting = false;
            error = 'Authentication timeout. Please try again.';
          }
        } catch (err) {
          console.error(`[${app}] Status check failed:`, err);
        }
      }, 2000);

      // Stop polling after 5 minutes
      setTimeout(() => {
        clearInterval(pollInterval);
        if (isConnecting) {
          isConnecting = false;
          error = 'Authentication timeout. Please try again.';
        }
      }, 300000);

    } catch (err) {
      isConnecting = false;
      error = err instanceof Error ? err.message : 'Failed to initiate authentication';
      console.error('Authentication error:', err);
    }
  }

  async function handleDisconnect() {
    if (!isConnected) return;

    try {
      // Implement disconnect if needed
      isConnected = false;
    } catch (err) {
      console.error('Failed to disconnect:', err);
    }
  }
</script>

<div class="auth-button-container">
  <button
    class="auth-button"
    class:connected={isConnected}
    class:connecting={isConnecting}
    on:click={isConnected ? handleDisconnect : handleConnect}
    disabled={isConnecting}
  >
    <span class="icon">{appIcons[app]}</span>
    <span class="text">
      {#if isConnecting}
        Connecting...
      {:else if isConnected}
        {appNames[app]} Connected
      {:else}
        Connect {appNames[app]}
      {/if}
    </span>
    {#if isConnected}
      <span class="status">✓</span>
    {/if}
  </button>
  
  {#if error}
    <div class="error">{error}</div>
  {/if}
</div>

<style>
  .auth-button-container {
    display: inline-block;
    margin: 0.5rem;
  }

  .auth-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.25rem;
    border: 2px solid #e5e7eb;
    border-radius: 0.75rem;
    background: white;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    min-width: 200px;
  }

  .auth-button:hover:not(:disabled) {
    border-color: #6366f1;
    background: #f0f9ff;
  }

  .auth-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .auth-button.connected {
    border-color: #10b981;
    background: #f0fdf4;
  }

  .auth-button.connecting {
    border-color: #f59e0b;
    background: #fffbeb;
  }

  .icon {
    font-size: 1.25rem;
  }

  .text {
    flex: 1;
    text-align: left;
  }

  .status {
    color: #10b981;
    font-weight: bold;
  }

  .error {
    margin-top: 0.5rem;
    padding: 0.5rem;
    background: #fee2e2;
    border: 1px solid #fecaca;
    border-radius: 0.375rem;
    color: #991b1b;
    font-size: 0.875rem;
  }
</style>