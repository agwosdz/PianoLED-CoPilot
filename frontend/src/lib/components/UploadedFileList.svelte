<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { formatFileSize } from '$lib/upload';

  export type UploadedFile = {
    filename: string;
    path: string;
    size: number;
    modified: string;
  };

  export let files: UploadedFile[] = [];
  export let selectedPath: string | null = null;

  const dispatch = createEventDispatcher<{
    select: { file: UploadedFile };
    play: { file: UploadedFile };
    delete: { file: UploadedFile };
  }>();

  function handleSelect(file: UploadedFile): void {
    dispatch('select', { file });
  }

  function handlePlay(file: UploadedFile, event: MouseEvent): void {
    event.stopPropagation();
    dispatch('play', { file });
  }

  function handleDelete(file: UploadedFile, event: MouseEvent): void {
    event.stopPropagation();
    dispatch('delete', { file });
  }

  function formatTimestamp(value: string): string {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  }

  function getDisplayName(filename: string): string {
    if (!filename) return '';
    const base = filename.split(/[\\/]/).pop() ?? filename;
    return base.replace(/_\d{8}_\d{6}_[a-f0-9]+(?=\.)/, '');
  }
</script>

<ul class="file-list" aria-label="Uploaded MIDI files">
  {#if files.length === 0}
    <li class="empty-state">No uploaded files yet.</li>
  {:else}
    {#each files as file (file.path)}
      <li class="file-row {selectedPath === file.path ? 'selected' : ''}">
        <button
          type="button"
          class="file-info"
          on:click={() => handleSelect(file)}
          title={getDisplayName(file.filename)}
        >
          <span class="file-name">{getDisplayName(file.filename)}</span>
          <span class="file-meta">{formatFileSize(file.size)} · {formatTimestamp(file.modified)}</span>
        </button>
        <div class="row-actions">
          <button
            type="button"
            class="icon-button"
            on:click={(event) => handlePlay(file, event)}
            aria-label={`Play ${getDisplayName(file.filename)}`}
            title={`Play ${getDisplayName(file.filename)}`}
          >
            <span aria-hidden="true">▶</span>
          </button>
          <button
            type="button"
            class="icon-button danger"
            on:click={(event) => handleDelete(file, event)}
            aria-label={`Delete ${getDisplayName(file.filename)}`}
            title={`Delete ${getDisplayName(file.filename)}`}
          >
            <span aria-hidden="true">🗑</span>
          </button>
        </div>
      </li>
    {/each}
  {/if}
</ul>

<style>
  .file-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
  }

  .empty-state {
    margin: 0;
    padding: 1rem;
    border-radius: 12px;
    background: #f1f5f9;
    color: #64748b;
    text-align: center;
    font-size: 0.95rem;
  }

  .file-row {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.85rem 1rem;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    background: #ffffff;
    box-shadow: 0 8px 16px rgba(15, 23, 42, 0.06);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  }

  .file-row:hover {
    transform: translateY(-1px);
    box-shadow: 0 12px 20px rgba(15, 23, 42, 0.08);
    border-color: #cbd5f5;
  }

  .file-row.selected {
    border-color: #2563eb;
    background: #eef2ff;
  }

  .file-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.35rem;
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
    text-align: left;
    cursor: pointer;
    color: inherit;
  }

  .file-name {
    font-weight: 600;
    font-size: 0.95rem;
    max-width: 100%;
    word-break: break-word;
    overflow-wrap: break-word;
    hyphens: auto;
    line-height: 1.3;
  }

  .file-meta {
    font-size: 0.8rem;
    color: #64748b;
  }

  .row-actions {
    display: inline-flex;
    gap: 0.5rem;
    flex-shrink: 0;
    align-self: center;
  }

  .icon-button {
    width: 2.25rem;
    height: 2.25rem;
    border-radius: 9999px;
    border: none;
    background: #e2e8f0;
    color: #1f2937;
    font-size: 0.95rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.2s ease, transform 0.2s ease;
  }

  .icon-button:hover {
    background: #cbd5f5;
    transform: translateY(-1px);
  }

  .icon-button:focus-visible {
    outline: 2px solid #2563eb;
    outline-offset: 2px;
  }

  .icon-button.danger {
    background: #fee2e2;
    color: #b91c1c;
  }

  .icon-button.danger:hover {
    background: #fecaca;
  }

  @media (max-width: 640px) {
    .file-row {
      flex-direction: column;
      align-items: stretch;
      gap: 0.75rem;
    }

    .row-actions {
      justify-content: flex-end;
    }
  }
</style>
