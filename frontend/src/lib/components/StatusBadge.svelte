<script lang="ts">
  import { onMount } from 'svelte';
  import { socketStatus } from '$lib/socket';
  import { writable, get } from 'svelte/store';

  type ApiState = 'up' | 'down' | 'unknown';
  const apiState = writable<ApiState>('unknown');

  let isDev = false;
  let host = '';
  let transport = 'unknown';
  let backendInfo = '';

  async function pingAPI(): Promise<ApiState> {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);
      const res = await fetch('/api/dashboard', { signal: controller.signal });
      clearTimeout(timeout);
      return res.ok ? 'up' : 'down';
    } catch {
      return 'down';
    }
  }

  function detectTransport() {
    try {
      const cfg = (window as any).socketIOConfig || {};
      const transports = Array.isArray(cfg.transports) ? cfg.transports : [];
      transport = transports.length ? transports[0] : 'unknown';
      const url = (window as any).socketIOBackendUrl || '';
      backendInfo = (url && typeof url === 'string') ? url : `${window.location.protocol}//${window.location.host}`;
    } catch {
      transport = 'unknown';
      backendInfo = `${window.location.protocol}//${window.location.host}`;
    }
  }

  onMount(async () => {
    host = typeof window !== 'undefined' ? window.location.host : '';
    isDev = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
    apiState.set(await pingAPI());
    detectTransport();
  });
</script>

<div class="status-badge" aria-label="Backend status">
  <div class="row">
    <span class="dot" class:ok={$apiState === 'up'} class:warn={$apiState === 'down'}></span>
    <span class="label">API</span>
    <span class="value">{$apiState === 'up' ? 'reachable' : $apiState === 'down' ? 'unreachable' : 'unknown'}</span>
  </div>
  <div class="row">
    <span class="dot" class:ok={$socketStatus === 'connected'} class:warn={$socketStatus === 'error' || $socketStatus === 'disconnected'}></span>
    <span class="label">Socket</span>
    <span class="value">{$socketStatus} · {transport}</span>
  </div>
  <div class="env">{isDev ? 'dev' : 'prod'} · {backendInfo}</div>
</div>

<style>
  .status-badge {
    display: inline-flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 12px;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #fafafa;
    color: #374151;
    font-size: 13px;
    align-items: flex-start;
    max-width: 420px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  }
  .row { display: inline-flex; align-items: center; gap: 8px; }
  .label { color: #6b7280; font-size: 12px; }
  .value { font-weight: 600; }
  .dot { width: 10px; height: 10px; border-radius: 9999px; background: #9ca3af; display: inline-block; }
  .dot.ok { background: #10b981; }
  .dot.warn { background: #ef4444; }
  .env { color: #6b7280; font-size: 12px; }
</style>