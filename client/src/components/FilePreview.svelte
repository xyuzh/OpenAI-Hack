<script lang="ts">
  import { initiateThread, executeThreadTask } from '../lib/thread';
  import { createEventDispatcher } from 'svelte';

  type DriveUser = {
    displayName: string;
    emailAddress: string;
    kind: string;
    me?: boolean;
    permissionId?: string;
    photoLink?: string;
  };

  type DrivePermission = {
    id?: string;
    kind: string;
    type?: string;
    role?: string;
    emailAddress?: string;
    displayName?: string;
    photoLink?: string;
    deleted?: boolean;
    pendingOwner?: boolean;
  };

  type DriveFile = {
    id: string;
    name: string;
    mimeType: string;
    createdTime: string;
    modifiedTime?: string;
    owners?: DriveUser[];
    lastModifyingUser?: DriveUser;
    permissions?: DrivePermission[];
    shared?: boolean;
    starred?: boolean;
    trashed?: boolean;
    size?: string;
    webViewLink?: string;
  };

  export let doc: DriveFile | null = null;
  export let onClose: () => void = () => {};
  export let entityId: string = 'default-user';
  
  const dispatch = createEventDispatcher();

  $: embedUrl = doc ? `https://docs.google.com/document/d/${doc.id}/preview` : '';

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.stopPropagation();
      onClose?.();
    }
  }

  let isGenerating: boolean = false;
  let generateError: string | null = null;

  async function handleGenerate() {
    if (!doc) return;
    isGenerating = true;
    generateError = null;
    
    try {
      // Step 1: Initialize a new thread
      console.log('Initializing thread...');
      const threadInit = await initiateThread({
        document_id: doc.id,
        document_name: doc.name
      });
      
      const threadId = threadInit.thread_id;
      console.log('Thread created:', threadId);
      
      // Step 2: Execute task to process document and create Jira tickets
      console.log('Executing task to process document...');
      const task = `Process this Google Doc and create Jira tickets for each action item or task found. 
                    Document: ${doc.name}
                    Please analyze the document content and create appropriate Jira issues with:
                    - Clear titles
                    - Detailed descriptions
                    - Appropriate issue types (Task, Story, Bug)
                    - Priority levels`;
      
      const executeResponse = await executeThreadTask(
        threadId,
        task,
        doc.id,
        entityId
      );
      
      console.log('Task execution started:', executeResponse);
      
      // Step 3: Dispatch event to switch to chat UI
      dispatch('startChat', {
        threadId: threadId,
        runId: executeResponse.run_id,
        documentId: doc.id,
        documentName: doc.name
      });
      
      // Close the preview
      onClose();
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      generateError = message;
      console.error('Generate failed:', err);
    } finally {
      isGenerating = false;
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if doc}
  <div class="fixed inset-0 z-50" role="dialog" aria-modal="true">
    <div class="absolute inset-0 bg-black/50" on:click={onClose} aria-hidden="true"></div>

    <div class="relative z-10 h-full w-full p-4 sm:p-6">
      <div class="mx-auto flex h-full w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-black/5">
        <div class="flex items-center justify-between gap-2 border-b px-4 py-3">
          <div class="min-w-0">
            <div class="truncate text-sm text-gray-500">Google Doc</div>
            <div class="truncate text-lg font-semibold text-gray-900" title={doc.name}>{doc.name}</div>
          </div>
          <div class="flex items-center gap-2">
            <button
              class="rounded-lg border border-transparent px-3 py-1.5 text-sm text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed"
              on:click={handleGenerate}
              disabled={isGenerating}
              aria-label="Generate"
            >
              {#if isGenerating}
                <div class="flex items-center">
                  <svg class="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Generating...
                </div>
              {:else}
                Generate
              {/if}
            </button>
            <button
              class="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-200"
              on:click={onClose}
              aria-label="Close preview"
            >
              Close
            </button>
          </div>
        </div>

        <div class="flex-1">
          <iframe
            src={embedUrl}
            title={doc.name}
            class="h-full w-full"
            allow="clipboard-write; fullscreen"
          ></iframe>
          {#if generateError}
            <div class="px-4 py-2 text-sm text-red-600">{generateError}</div>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  /* Ensure the iframe takes full remaining height */
  .flex-1 { flex: 1 1 auto; }
  iframe { border: 0; }
</style>
