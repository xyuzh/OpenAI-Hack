<script lang="ts">
    // --- Types ---------------------------------------------------------------
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
      mimeType: string; // e.g. "application/vnd.google-apps.document"
      createdTime: string; // ISO
      modifiedTime?: string; // ISO
      owners?: DriveUser[];
      lastModifyingUser?: DriveUser;
      permissions?: DrivePermission[];
      shared?: boolean;
      starred?: boolean;
      trashed?: boolean;
      size?: string; // string in API; bytes
      webViewLink?: string;
    };
  
    type DriveList = {
      documents: DriveFile[];
      next_page_token?: string | null;
      total_found?: number;
    };
  
    // --- Props ---------------------------------------------------------------
    import FilePreview from './FilePreview.svelte';

    export let documents: DriveFile[] = [];
    /** Called when a row is opened (double-click or Enter/Space). */
    export let onOpen: (doc: DriveFile) => void = () => {};
    /** Optional: initial sort field */
    export let initialSort: { field: 'name' | 'createdTime' | 'modifiedTime'; dir: 'asc' | 'desc' } = {
      field: 'modifiedTime',
      dir: 'desc'
    };
  
    // --- Local state ---------------------------------------------------------
    let sortField: 'name' | 'createdTime' | 'modifiedTime' = initialSort.field;
    let sortDir: 'asc' | 'desc' = initialSort.dir;
    let query = '';
    let previewDoc: DriveFile | null = null;
  
    $: filtered = query.trim()
      ? documents.filter((d) =>
          [d.name, d.lastModifyingUser?.displayName, d.owners?.[0]?.displayName, d.lastModifyingUser?.emailAddress]
            .filter(Boolean)
            .some((s) => s!.toLowerCase().includes(query.toLowerCase()))
        )
      : documents;
  
    $: rows = [...filtered].sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1;
      if (sortField === 'name') return a.name.localeCompare(b.name) * dir;
      if (sortField === 'createdTime') return (new Date(a.createdTime).getTime() - new Date(b.createdTime).getTime()) * dir;
      // modifiedTime fallback to createdTime if missing
      const am = new Date(a.modifiedTime ?? a.createdTime).getTime();
      const bm = new Date(b.modifiedTime ?? b.createdTime).getTime();
      return (am - bm) * dir;
    });
  
    function setSort(field: typeof sortField) {
      if (sortField === field) {
        sortDir = sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        sortField = field;
        sortDir = field === 'name' ? 'asc' : 'desc';
      }
    }
  
    function onRowDblClick(doc: DriveFile) {
      previewDoc = doc;
      onOpen?.(doc);
    }
  
    function onRowKeydown(e: KeyboardEvent, doc: DriveFile) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        previewDoc = doc;
        onOpen?.(doc);
      }
    }
  
    // --- Utils ---------------------------------------------------------------
    function humanFileSize(sizeStr?: string) {
      if (!sizeStr) return '—';
      const bytes = Number(sizeStr);
      if (!isFinite(bytes) || bytes <= 0) return '—';
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      let i = 0;
      let num = bytes;
      while (num >= 1024 && i < units.length - 1) {
        num /= 1024;
        i++;
      }
      return `${num.toFixed(num < 10 && i > 0 ? 1 : 0)} ${units[i]}`;
      }
  
    function formatDate(iso?: string) {
      if (!iso) return '—';
      const d = new Date(iso);
      if (isNaN(d.getTime())) return '—';
      // Shown as local date/time; change to your locale needs if desired.
      return d.toLocaleString([], {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  
    function fileKind(mime: string) {
      // Simplified kind label
      if (mime.includes('document')) return 'Doc';
      if (mime.includes('spreadsheet')) return 'Sheet';
      if (mime.includes('presentation')) return 'Slide';
      return 'File';
    }
  
    function kindIcon(mime: string) {
      // Emoji fallback for simplicity; swap with SVGs as desired.
      if (mime.includes('document')) return '📝';
      if (mime.includes('spreadsheet')) return '📊';
      if (mime.includes('presentation')) return '📑';
      return '📄';
    }
  
    function titleFor(doc: DriveFile) {
      const owner = doc.owners?.[0]?.displayName ?? doc.owners?.[0]?.emailAddress ?? 'Unknown';
      const lm = doc.lastModifyingUser?.displayName ?? doc.lastModifyingUser?.emailAddress ?? '—';
      return `${doc.name}\nOwner: ${owner}\nLast modified by: ${lm}`;
    }
  </script>
  
  <!-- Container -->
  <div class="w-full">
    <!-- Toolbar -->
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mb-3">
      <div class="text-xl font-semibold tracking-tight">Google Docs</div>
      <div class="flex items-center gap-2">
        <input
          type="search"
          placeholder="Search by title, owner, or modifier…"
          bind:value={query}
          class="w-full sm:w-80 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none ring-0 focus:border-gray-300 focus:ring-2 focus:ring-indigo-100"
        />
      </div>
    </div>
  
    <!-- Table -->
    <div class="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div class="grid grid-cols-12 bg-gray-50 text-xs font-medium uppercase tracking-wider text-gray-600">
        <button
          class="col-span-6 sm:col-span-5 text-left px-4 py-3 hover:bg-gray-100 flex items-center gap-2"
          on:click={() => setSort('name')}
          aria-label="Sort by name"
        >
          <span>Title</span>
          {#if sortField === 'name'}<span class="text-gray-400">{sortDir === 'asc' ? '▲' : '▼'}</span>{/if}
        </button>
  
        <button
          class="hidden sm:flex col-span-2 items-center gap-2 px-2 py-3 hover:bg-gray-100"
          on:click={() => setSort('createdTime')}
          aria-label="Sort by created time"
        >
          <span>Created</span>
          {#if sortField === 'createdTime'}<span class="text-gray-400">{sortDir === 'asc' ? '▲' : '▼'}</span>{/if}
        </button>
  
        <button
          class="col-span-3 sm:col-span-2 flex items-center gap-2 px-2 py-3 hover:bg-gray-100"
          on:click={() => setSort('modifiedTime')}
          aria-label="Sort by modified time"
        >
          <span>Modified</span>
          {#if sortField === 'modifiedTime'}<span class="text-gray-400">{sortDir === 'asc' ? '▲' : '▼'}</span>{/if}
        </button>
  
        <div class="hidden sm:block col-span-2 px-2 py-3">Owner</div>
        <div class="col-span-1 px-2 py-3 text-center">Size</div>
      </div>
  
      {#if rows.length === 0}
        <div class="p-10 text-center text-sm text-gray-500">
          No files match your search.
        </div>
      {:else}
        <ul role="list" class="divide-y divide-gray-100">
          {#each rows as doc (doc.id)}
            <li
              class="grid grid-cols-12 items-center hover:bg-indigo-50/40 focus:bg-indigo-50/70 focus:outline-none cursor-default"
              title={titleFor(doc)}
              
              on:dblclick={() => onRowDblClick(doc)}
              on:keydown={(e) => onRowKeydown(e, doc)}
              aria-label={`Open ${doc.name}`}
            >
              <!-- Title / Kind / Shared/Starred -->
              <div class="col-span-6 sm:col-span-5 flex items-center gap-3 px-4 py-3 min-w-0">
                <div class="shrink-0 text-lg" aria-hidden="true">{kindIcon(doc.mimeType)}</div>
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="truncate font-medium">{doc.name}</span>
                    {#if doc.shared}
                      <span class="text-[10px] rounded-md border border-gray-300 px-1.5 py-0.5 text-gray-600 bg-white">Shared</span>
                    {/if}
                    {#if doc.starred}
                      <span class="text-yellow-500" aria-label="Starred">★</span>
                    {/if}
                    <span class="text-[10px] rounded-md bg-gray-100 px-1.5 py-0.5 text-gray-600">{fileKind(doc.mimeType)}</span>
                  </div>
                  <div class="mt-0.5 flex items-center gap-2 text-xs text-gray-500">
                    <span>by {doc.owners?.[0]?.displayName ?? doc.owners?.[0]?.emailAddress ?? 'Unknown'}</span>
                    <span aria-hidden="true">•</span>
                    <span class="truncate">Last modified by {doc.lastModifyingUser?.displayName ?? doc.lastModifyingUser?.emailAddress ?? '—'}</span>
                  </div>
                </div>
              </div>
  
              <!-- Created -->
              <div class="hidden sm:block col-span-2 px-2 py-3 text-sm text-gray-600">{formatDate(doc.createdTime)}</div>
  
              <!-- Modified -->
              <div class="col-span-3 sm:col-span-2 px-2 py-3 text-sm text-gray-600">
                {formatDate(doc.modifiedTime ?? doc.createdTime)}
              </div>
  
              <!-- Owner avatar (desktop) -->
              <div class="hidden sm:flex col-span-2 items-center gap-2 px-2 py-3">
                {#if doc.owners?.[0]?.photoLink}
                  <img
                    src={doc.owners[0].photoLink}
                    alt="Owner avatar"
                    class="h-6 w-6 rounded-full ring-1 ring-gray-200 object-cover"
                    loading="lazy"
                    decoding="async"
                  />
                {/if}
                <span class="truncate text-sm text-gray-700">{doc.owners?.[0]?.displayName ?? '—'}</span>
              </div>
  
              <!-- Size + quick actions -->
              <div class="col-span-1 flex items-center justify-between px-2 py-3">
                <span class="text-xs text-gray-600">{humanFileSize(doc.size)}</span>
                {#if doc.webViewLink}
                  <a
                    href={doc.webViewLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="ml-2 rounded-lg border border-transparent px-2 py-1 text-xs text-indigo-600 hover:bg-indigo-50 hover:border-indigo-100"
                    on:click={(e) => e.stopPropagation()}
                    title="Open in Google Docs"
                  >
                    Open
                  </a>
                {/if}
              </div>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  
    <!-- Footer summary -->
    <div class="mt-3 text-xs text-gray-500">
      Showing {rows.length} {rows.length === 1 ? 'item' : 'items'}
      {#if typeof window !== 'undefined' && documents?.length !== rows.length}
        (filtered from {documents.length})
      {/if}
    </div>
  </div>
  
  {#if previewDoc}
    <FilePreview doc={previewDoc} onClose={() => (previewDoc = null)} />
  {/if}

  <style>
    /* Optional: improve focus ring on list rows */
    li[tabindex="0"]:focus {
      outline: none;
      box-shadow: 0 0 0 2px rgb(199 210 254 / 0.8) inset;
    }
  </style>
  