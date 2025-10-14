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

  const dispatch = createEventDispatcher<{ select: { file: UploadedFile } }>();

  function handleSelect(file: UploadedFile): void {
    dispatch('select', { file });
  }

  function formatTimestamp(value: string): string {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  }
</script>

<div class="file-list" role="list" aria-label="Uploaded MIDI files">
  {#if files.length === 0}
    <p class="empty-state">No uploaded files yet.</p>
  {:else}
    {#each files as file (file.path)}
      <button
        type="button"
        role="listitem"
        class="file-item {selectedPath === file.path ? 'selected' : ''}"
        on:click={() => handleSelect(file)}
      >
        <span class="file-name">{file.filename}</span>
        <span class="file-meta">{formatFileSize(file.size)} · {formatTimestamp(file.modified)}</span>
      </button>
    {/each}
  {/if}
</div>

<style>
  .file-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .empty-state {
    margin: 0;
    color: #64748b;
    font-size: 0.9rem;
  }

  .file-item {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
    padding: 0.75rem 1rem;
    width: 100%;
    border-radius: 10px;
    border: 1px solid transparent;
    background: #f1f5f9;
    color: #0f172a;
    cursor: pointer;
    transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
    text-align: left;
  }

  .file-item:hover {
    background: #e2e8f0;
    border-color: #cbd5f5;
    transform: translateY(-1px);
  }

  .file-item.selected {
    background: rgba(37, 99, 235, 0.1);
    border-color: #2563eb;
    color: #1d4ed8;
  }

  .file-name {
    font-weight: 600;
  }

  .file-meta {
    font-size: 0.8rem;
    color: #475569;
  }
</style>
