<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { socketStatus } from '$lib/socket';

	let isOpen = false;
	let mounted = false;
	let isMobile = false;
	$: wsConnected = $socketStatus === 'connected';

	function toggleMenu() {
		isOpen = !isOpen;
	}

	function closeMenu() {
		isOpen = false;
	}

	function handleResize() {
		isMobile = window.innerWidth <= 768;
		if (!isMobile) {
			isOpen = false; // Close mobile menu when switching to desktop
		}
	}

	onMount(() => {
		mounted = true;
		handleResize();
		window.addEventListener('resize', handleResize);
		
		return () => {
			window.removeEventListener('resize', handleResize);
		};
	});

	$: currentPath = $page.url.pathname;

	const navigationItems = [
		{ href: '/', icon: '🏠', text: 'Home', description: 'Main dashboard and overview' },
		{ href: '/play', icon: '🎹', text: 'Play', description: 'MIDI playback and visualization' },
		{ href: '/upload', icon: '📤', text: 'Upload', description: 'Upload MIDI files' },
		{ href: '/settings', icon: '⚙️', text: 'Settings', description: 'Configuration and preferences' }
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

<!-- Mobile Navigation -->
<div class="mobile-nav-container {mounted ? 'mounted' : ''}">
	<button 
		class="menu-toggle" 
		on:click={toggleMenu}
		aria-label="{isOpen ? 'Close menu' : 'Open menu'}"
		aria-expanded={isOpen}
	>
		<div class="hamburger {isOpen ? 'open' : ''}">
			<span></span>
			<span></span>
			<span></span>
		</div>
	</button>

	<nav class="mobile-nav {isOpen ? 'open' : ''}" aria-hidden={!isOpen} aria-label="Mobile navigation">
		<div class="mobile-nav-header">
			<div class="mobile-logo">
				<span class="logo-icon">🎹</span>
				<span class="logo-text">Piano LED Visualizer</span>
			</div>
			<div class="socket-indicator {wsConnected ? 'connected' : 'disconnected'}" title={wsConnected ? 'Socket Connected' : 'Socket Disconnected'}>
				<span class="dot"></span>
				<span class="text">{wsConnected ? 'Connected' : 'Disconnected'}</span>
			</div>
		</div>
		
		<ul class="mobile-nav-list">
			{#each navigationItems as item}
				<li>
					<a 
						href={item.href}
						class:active={currentPath === item.href}
						on:click={closeMenu}
					>
						<span class="icon">{item.icon}</span>
						<div class="nav-content">
							<span class="text">{item.text}</span>
							<span class="description">{item.description}</span>
						</div>
					</a>
				</li>
			{/each}
		</ul>
	</nav>

	{#if isOpen}
		<div class="overlay" on:click={closeMenu} aria-hidden="true"></div>
	{/if}
</div>

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

	/* Mobile Navigation Styles */
	.mobile-nav-container {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		z-index: 200;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: linear-gradient(180deg, #0f172a 0%, #0f172a 100%);
		border-bottom: 1px solid #334155;
		padding: 0.5rem 1rem;
	}

	.menu-toggle {
		background: none;
		border: none;
		color: #f8fafc;
	}

	.hamburger {
		width: 24px;
		height: 16px;
		position: relative;
	}

	.hamburger span {
		position: absolute;
		left: 0;
		right: 0;
		height: 2px;
		background: #f8fafc;
		transition: transform 0.2s ease;
	}

	.hamburger span:nth-child(1) { top: 0; }
	.hamburger span:nth-child(2) { top: 7px; }
	.hamburger span:nth-child(3) { top: 14px; }

	.hamburger.open span:nth-child(1) { transform: translateY(7px) rotate(45deg); }
	.hamburger.open span:nth-child(2) { opacity: 0; }
	.hamburger.open span:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }

	.mobile-nav {
		position: fixed;
		top: 48px;
		left: 0;
		right: 0;
		background: #0f172a;
		border-bottom: 1px solid #334155;
		transform: translateY(-110%);
		transition: transform 0.3s ease;
	}
	.mobile-nav.open { transform: translateY(0); }

	.mobile-nav-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
		color: #f8fafc;
	}

	.mobile-logo {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.mobile-nav-list {
		list-style: none;
		margin: 0;
		padding: 0.5rem 0;
	}

	.mobile-nav-list a {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		color: #cbd5e1;
		text-decoration: none;
	}

	.mobile-nav-list a.active {
		background: rgba(255, 255, 255, 0.08);
		color: white;
	}

	.overlay {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.4);
	}
</style>