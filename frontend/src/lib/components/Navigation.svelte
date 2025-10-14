<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { socketStatus } from '$lib/socket';

	let mounted = false;
	$: wsConnected = $socketStatus === 'connected';

	onMount(() => {
		mounted = true;
	});

	$: currentPath = $page.url.pathname;
	$: currentHash = ($page.url.hash ?? '').replace('#', '');

	const navigationItems = [
		{ href: '/', icon: '🏠', text: 'Home', description: 'System overview and status' },
		{ href: '/listen', icon: '🎧', text: 'Listen', description: 'Upload and play MIDI files' },
		{
			href: '/settings',
			icon: '⚙️',
			text: 'Settings',
			description: 'Configuration and preferences',
			children: [
				{ hash: 'piano-settings', icon: '🎹', text: 'Piano Setup' },
				{ hash: 'led-settings', icon: '💡', text: 'LED Strip' },
				{ hash: 'midi-settings', icon: '🎛️', text: 'MIDI Connections' },
				{ hash: 'calibration-settings', icon: '🛠️', text: 'Calibration' }
			]
		}
	];
</script>

<!-- Desktop Sidebar Navigation -->
<nav class="desktop-nav {mounted ? 'mounted' : ''}" aria-label="Main navigation">
	<div class="nav-header">
		<div class="logo">
			<span class="logo-icon">🎹</span>
			<span class="logo-text">Piano LED</span>
		</div>
	</div>
	
	<ul class="nav-list">
		{#each navigationItems as item}
			{#if item.children && item.children.length > 0}
				<li class:has-children={currentPath.startsWith(item.href)}>
					<a
						href={item.href}
						class:active={currentPath.startsWith(item.href)}
						title={item.description}
					>
						<span class="nav-icon">{item.icon}</span>
						<span class="nav-text">{item.text}</span>
					</a>

					{#if currentPath.startsWith(item.href)}
						<ul class="sub-nav" aria-label={`${item.text} subsections`}>
							{#each item.children as child, index}
								<li>
									<a
										href={`${item.href}#${child.hash}`}
										class:active={currentHash === child.hash || (!currentHash && index === 0)}
									>
										<span class="nav-icon" aria-hidden="true">{child.icon}</span>
										<span class="nav-text">{child.text}</span>
									</a>
								</li>
							{/each}
						</ul>
					{/if}
				</li>
			{:else}
				<li>
					<a
						href={item.href}
						class:active={currentPath === item.href}
						title={item.description}
					>
						<span class="nav-icon">{item.icon}</span>
						<span class="nav-text">{item.text}</span>
					</a>
				</li>
			{/if}
		{/each}
	</ul>
	
	<div class="nav-footer">
		<div class="version-info">
			<span class="version-text">v1.0.0</span>
		</div>
		<div class="socket-indicator {wsConnected ? 'connected' : 'disconnected'}" title={wsConnected ? 'Socket Connected' : 'Socket Disconnected'}>
			<span class="dot"></span>
			<span class="text">{wsConnected ? 'Connected' : 'Disconnected'}</span>
		</div>
	</div>
</nav>

<style>
	/* Desktop Navigation Styles */
	.desktop-nav {
		position: fixed;
		top: 0;
		left: 0;
		width: 280px;
		height: 100vh;
		background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
		border-right: 1px solid #334155;
		display: flex;
		flex-direction: column;
		z-index: 100;
		opacity: 0;
		transform: translateX(-100%);
		transition: all 0.3s ease;
	}

	.desktop-nav.mounted {
		opacity: 1;
		transform: translateX(0);
	}

	.nav-header {
		padding: 2rem 1.5rem 1.5rem;
		border-bottom: 1px solid #334155;
	}

	.logo {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.logo-icon {
		font-size: 2rem;
		filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
	}

	.logo-text {
		font-size: 1.25rem;
		font-weight: 700;
		color: #f8fafc;
		letter-spacing: -0.025em;
	}

	.nav-list {
		flex: 1;
		list-style: none;
		padding: 1rem 0;
		margin: 0;
		overflow-y: auto;
	}

	.nav-list li {
		margin: 0.25rem 0;
	}

	.nav-list li.has-children > a {
		margin-bottom: 0.25rem;
	}

	.sub-nav {
		list-style: none;
		margin: 0;
		padding: 0 0 0 2.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}

	.sub-nav a {
		display: inline-flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.55rem 0.75rem;
		color: #e2e8f0;
		text-decoration: none;
		border-radius: 8px;
		background: rgba(148, 163, 184, 0.08);
		font-size: 0.85rem;
		font-weight: 600;
		transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
	}

	.sub-nav a:hover,
	.sub-nav a:focus {
		background: rgba(148, 163, 184, 0.18);
		color: #ffffff;
		transform: translateX(2px);
		outline: none;
	}

	.sub-nav a.active {
		background: rgba(96, 165, 250, 0.3);
		color: #ffffff;
	}

	.sub-nav .nav-icon {
		font-size: 1rem;
	}

	.nav-list a {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		color: #cbd5e1;
		text-decoration: none;
		border-radius: 8px;
	}

	.nav-list a.active {
		background: rgba(255, 255, 255, 0.1);
		color: white;
	}

	.nav-icon {
		font-size: 1.25rem;
	}

	.nav-text {
		font-weight: 600;
	}

	.nav-footer {
		padding: 1rem 1.5rem;
		border-top: 1px solid #334155;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
	}
	.socket-indicator {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.375rem 0.75rem;
		border-radius: 9999px;
		font-size: 0.75rem;
		font-weight: 600;
		color: #cbd5e1;
		background: rgba(255,255,255,0.1);
	}
	.socket-indicator.connected {
		background: rgba(34, 197, 94, 0.15);
		color: #22c55e;
	}
	.socket-indicator.disconnected {
		background: rgba(239, 68, 68, 0.15);
		color: #ef4444;
	}
	.socket-indicator .dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: currentColor;
	}

	/* Mobile Layout */
	@media (max-width: 768px) {
		/* Mobile layout adjustments are handled by the consuming layout; these
		   selectors were unused and removed to quiet svelte-check warnings. */
	}
</style>