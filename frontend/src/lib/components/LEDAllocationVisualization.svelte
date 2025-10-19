<script lang="ts">
  import { selectedKeyInfo, getMidiNoteName } from '$lib/stores/ledSelection';

  export let showVisualization = true;

  interface AllocationChange {
    ledIndex: number;
    from: string | null;
    to: string | null;
  }

  let changes: AllocationChange[] = [];

  $: if ($selectedKeyInfo) {
    // Build change list
    const changeMap = new Map<number, AllocationChange>();

    // Track removed LEDs
    for (const ledIndex of $selectedKeyInfo.removedLEDs) {
      changeMap.set(ledIndex, {
        ledIndex,
        from: getMidiNoteName($selectedKeyInfo.midiNote),
        to: null
      });
    }

    // Track where they went
    for (const [targetKey, leds] of Object.entries($selectedKeyInfo.reallocatedFrom)) {
      for (const ledIndex of leds) {
        const existing = changeMap.get(ledIndex) || {
          ledIndex,
          from: null,
          to: null
        };
        existing.to = getMidiNoteName(parseInt(targetKey, 10));
        changeMap.set(ledIndex, existing);
      }
    }

    changes = Array.from(changeMap.values());
  }
</script>

{#if showVisualization && $selectedKeyInfo}
  <div class="led-allocation-visualization">
    <h4>🎨 LED Allocation Visualization</h4>

    <!-- Before/After Comparison -->
    <div class="comparison-grid">
      <div class="allocation-view">
        <div class="view-header">
          <span class="view-title">Before Override</span>
          <span class="led-count">{$selectedKeyInfo.baseAllocation.length} LEDs</span>
        </div>
        <div class="allocation-display">
          {#each $selectedKeyInfo.baseAllocation as led}
            <div class="led-badge base">
              <span>{led}</span>
            </div>
          {/each}
          {#if $selectedKeyInfo.baseAllocation.length === 0}
            <span class="empty-state">No LEDs assigned</span>
          {/if}
        </div>
      </div>

      <div class="arrow">
        <span>→</span>
      </div>

      <div class="allocation-view">
        <div class="view-header">
          <span class="view-title">After Override</span>
          <span class="led-count">{$selectedKeyInfo.currentAllocation.length} LEDs</span>
        </div>
        <div class="allocation-display">
          {#each $selectedKeyInfo.currentAllocation as led}
            {@const isRemoved = $selectedKeyInfo.removedLEDs.includes(led)}
            {@const isAdded = $selectedKeyInfo.addedLEDs.includes(led)}
            
            <div class="led-badge" class:removed={isRemoved} class:added={isAdded}>
              <span>{led}</span>
              {#if isRemoved}
                <span class="indicator" title="Removed">✕</span>
              {/if}
              {#if isAdded}
                <span class="indicator" title="Added">+</span>
              {/if}
            </div>
          {/each}
          {#if $selectedKeyInfo.currentAllocation.length === 0}
            <span class="empty-state">No LEDs assigned</span>
          {/if}
        </div>
      </div>
    </div>

    <!-- Change Summary -->
    {#if $selectedKeyInfo.removedLEDs.length > 0 || $selectedKeyInfo.addedLEDs.length > 0}
      <div class="change-summary">
        <div class="change-stat">
          <span class="stat-label">Removed:</span>
          <span class="stat-value removed">{$selectedKeyInfo.removedLEDs.length}</span>
          <span class="stat-detail">{$selectedKeyInfo.removedLEDs.join(', ') || 'none'}</span>
        </div>

        <div class="change-stat">
          <span class="stat-label">Added:</span>
          <span class="stat-value added">{$selectedKeyInfo.addedLEDs.length}</span>
          <span class="stat-detail">{$selectedKeyInfo.addedLEDs.join(', ') || 'none'}</span>
        </div>
      </div>
    {/if}

    <!-- Reallocation Details -->
    {#if changes.length > 0}
      <div class="reallocation-details">
        <h5>LED Reallocation</h5>
        <div class="reallocation-list">
          {#each changes as change}
            <div class="reallocation-item">
              <span class="led-index">LED {change.ledIndex}</span>
              <span class="reallocation-path">
                {#if change.from}
                  <span class="from-key">{change.from}</span>
                  <span class="arrow">→</span>
                {/if}
                {#if change.to}
                  <span class="to-key">{change.to}</span>
                {/if}
              </span>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Impact Analysis -->
    <div class="impact-analysis">
      <h5>Impact Analysis</h5>
      <div class="impact-list">
        {#if Object.keys($selectedKeyInfo.reallocatedFrom).length > 0}
          <div class="impact-item outgoing">
            <span class="impact-title">Reallocated from {getMidiNoteName($selectedKeyInfo.midiNote)}:</span>
            <div class="impact-details">
              {#each Object.entries($selectedKeyInfo.reallocatedFrom) as [targetKey, leds]}
                <span class="impact-detail">
                  → {getMidiNoteName(parseInt(targetKey, 10))}: LEDs {leds.join(', ')}
                </span>
              {/each}
            </div>
          </div>
        {/if}

        {#if Object.keys($selectedKeyInfo.reallocatedTo).length > 0}
          <div class="impact-item incoming">
            <span class="impact-title">Reallocated to {getMidiNoteName($selectedKeyInfo.midiNote)}:</span>
            <div class="impact-details">
              {#each Object.entries($selectedKeyInfo.reallocatedTo) as [sourceKey, leds]}
                <span class="impact-detail">
                  ← {getMidiNoteName(parseInt(sourceKey, 10))}: LEDs {leds.join(', ')}
                </span>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .led-allocation-visualization {
    background: white;
    border-radius: 6px;
    padding: 16px;
    border: 1px solid var(--border-color, #ddd);
    margin-top: 16px;
  }

  .led-allocation-visualization h4 {
    margin: 0 0 16px 0;
    color: var(--text-primary, #333);
    font-size: 1rem;
  }

  .comparison-grid {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 12px;
    align-items: center;
    margin-bottom: 20px;
  }

  .allocation-view {
    border: 1px solid var(--border-color, #ddd);
    border-radius: 6px;
    overflow: hidden;
  }

  .view-header {
    background: var(--bg-tertiary, #fafafa);
    padding: 10px 12px;
    border-bottom: 1px solid var(--border-color, #ddd);
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.9rem;
  }

  .view-title {
    font-weight: 600;
    color: var(--text-primary, #333);
  }

  .led-count {
    background: var(--primary-color, #007bff);
    color: white;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.8rem;
    font-weight: 500;
  }

  .allocation-display {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 12px;
    min-height: 50px;
    align-content: flex-start;
  }

  .led-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--primary-color, #007bff);
    color: white;
    padding: 6px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 600;
    position: relative;
  }

  .led-badge.base {
    background: var(--primary-color, #007bff);
  }

  .led-badge.removed {
    background: #e7d4d4;
    color: #8b5a5a;
    text-decoration: line-through;
    opacity: 0.6;
  }

  .led-badge.added {
    background: #d4e7d4;
    color: #5a8b5a;
    border: 2px solid #5a8b5a;
  }

  .led-badge .indicator {
    position: absolute;
    top: -6px;
    right: -6px;
    background: white;
    border-radius: 50%;
    width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.6rem;
    font-weight: bold;
  }

  .led-badge.removed .indicator {
    background: #c82333;
    color: white;
  }

  .led-badge.added .indicator {
    background: #28a745;
    color: white;
  }

  .arrow {
    font-size: 1.5rem;
    color: var(--text-secondary, #666);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .empty-state {
    color: var(--text-secondary, #666);
    font-size: 0.9rem;
    font-style: italic;
  }

  .change-summary {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 20px;
  }

  .change-stat {
    background: var(--bg-tertiary, #fafafa);
    border: 1px solid var(--border-color, #ddd);
    border-radius: 6px;
    padding: 12px;
  }

  .stat-label {
    display: block;
    font-size: 0.85rem;
    color: var(--text-secondary, #666);
    font-weight: 500;
    margin-bottom: 4px;
  }

  .stat-value {
    display: inline-block;
    font-size: 1.5rem;
    font-weight: bold;
    margin-right: 8px;
  }

  .stat-value.removed {
    color: #c82333;
  }

  .stat-value.added {
    color: #28a745;
  }

  .stat-detail {
    display: block;
    font-size: 0.8rem;
    color: var(--text-secondary, #666);
    font-family: monospace;
    margin-top: 4px;
  }

  .reallocation-details {
    background: var(--bg-tertiary, #fafafa);
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 16px;
  }

  .reallocation-details h5 {
    margin: 0 0 10px 0;
    font-size: 0.9rem;
    color: var(--text-primary, #333);
  }

  .reallocation-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .reallocation-item {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.85rem;
  }

  .led-index {
    background: white;
    border: 1px solid var(--border-color, #ddd);
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 600;
    color: var(--text-primary, #333);
    min-width: 50px;
    text-align: center;
  }

  .reallocation-path {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .from-key,
  .to-key {
    background: white;
    border: 1px solid var(--border-color, #ddd);
    padding: 2px 8px;
    border-radius: 3px;
    font-weight: 600;
    color: var(--text-secondary, #666);
  }

  .reallocation-path .arrow {
    font-size: 1rem;
    margin: 0;
    color: var(--text-secondary, #666);
  }

  .impact-analysis {
    background: var(--bg-secondary, #f5f5f5);
    border-radius: 6px;
    padding: 12px;
  }

  .impact-analysis h5 {
    margin: 0 0 12px 0;
    font-size: 0.9rem;
    color: var(--text-primary, #333);
  }

  .impact-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .impact-item {
    border-left: 3px solid var(--border-color, #ddd);
    padding: 10px 12px;
    background: white;
    border-radius: 3px;
  }

  .impact-item.outgoing {
    border-left-color: #dc3545;
  }

  .impact-item.incoming {
    border-left-color: #28a745;
  }

  .impact-title {
    display: block;
    font-weight: 600;
    font-size: 0.85rem;
    color: var(--text-primary, #333);
    margin-bottom: 6px;
  }

  .impact-details {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .impact-detail {
    font-size: 0.8rem;
    color: var(--text-secondary, #666);
    font-family: monospace;
  }

  @media (max-width: 768px) {
    .comparison-grid {
      grid-template-columns: 1fr;
      gap: 8px;
    }

    .arrow {
      writing-mode: vertical-rl;
      text-orientation: mixed;
      transform: rotate(180deg);
      margin: 4px 0;
    }

    .change-summary {
      grid-template-columns: 1fr;
    }
  }
</style>
