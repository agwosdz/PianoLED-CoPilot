<script>
	import { createEventDispatcher } from 'svelte';
	import { get } from 'svelte/store';
	import { lastSavedSettings, savingSettings, failedSettings } from '$lib/stores/settings.js';
	
	const dispatch = createEventDispatcher();
	
	export let type = 'text';
	export let label = '';
	export let value = '';
	export let placeholder = '';
	export let required = false;
	export let disabled = false;
	export let error = '';
	export let helpText = '';
	export let min = undefined;
	export let max = undefined;
	export let step = undefined;
	export let options = []; // For select fields
	export let loading = false;
	export let validationState = 'none'; // 'none', 'validating', 'valid', 'invalid'
	export let id = '';
	export let category = '';
	export let settingKey = '';
	
	// Generate unique ID if not provided
	if (!id) {
		id = `field-${Math.random().toString(36).substr(2, 9)}`;
	}
	
	function handleInput(event) {
		let newValue = event.target.value;
		
		// Convert to appropriate type for number inputs
		if (type === 'number' || type === 'range') {
			newValue = parseFloat(newValue);
			// Handle NaN case
			if (isNaN(newValue)) {
				newValue = 0;
			}
		}
		
		value = newValue;
		dispatch('input', { value: newValue, id });
	}
	
	function handleChange(event) {
		let newValue;
		if (type === 'checkbox') {
			newValue = event.target.checked;
		} else {
			newValue = event.target.value;
			if (type === 'number' || type === 'range') {
				newValue = parseFloat(newValue);
				if (isNaN(newValue)) newValue = 0;
			}
		}
		value = newValue;
		dispatch('change', { value: newValue, id });
	}
	
	$: hasError = error && error.length > 0;
	// Persisted-state support
	function readNested(obj, path) {
	  if (!obj || !path) return undefined;
	  const parts = String(path).split('.');
	  let curr = obj;
	  for (const p of parts) {
	    if (curr && typeof curr === 'object' && p in curr) {
	      curr = curr[p];
	    } else {
	      return undefined;
	    }
	  }
	  return curr;
	}
	
	$: persisted = (() => {
	  try {
	    if (!category || !settingKey) return false;
	    const savedAll = get(lastSavedSettings) || {};
	    const savedCategory = savedAll[category] || {};
	    const savedValue = readNested(savedCategory, settingKey);
	    if (savedValue === undefined) return false;
	    const normalize = (v) => (typeof v === 'object' ? JSON.stringify(v) : String(v));
	    return normalize(savedValue) === normalize(value);
	  } catch {
	    return false;
	  }
	})();
	
	$: isSaving = !!(get(savingSettings)?.[category]?.[settingKey]);
	$: failedMessage = (get(failedSettings)?.[category]?.[settingKey]) || '';
	$: isValidating = isSaving || validationState === 'validating' || !!failedMessage;
	$: isValid = persisted && !isValidating && validationState !== 'invalid';
	// Range slider progress computation
	$: rangeMin = Number(min ?? 0);
	$: rangeMax = Number(max ?? 100);
	$: rangeVal = Number(value ?? rangeMin);
	$: rangeProgress = Math.min(100, Math.max(0, Math.round(((rangeVal - rangeMin) / Math.max(rangeMax - rangeMin, 1)) * 100)));
</script>

<div class="form-field" class:has-error={hasError} class:is-valid={isValid}>
	{#if label && type !== 'checkbox'}
		<label for={id} class="field-label">
			{label}
			{#if required}
				<span class="required-indicator">*</span>
			{/if}
		</label>
	{/if}
	
	<div class="field-wrapper">
		{#if type === 'select'}
			<select
				{id}
				bind:value
				{disabled}
				{required}
				on:change={handleChange}
				class="field-input select-input"
				class:loading
			>
				{#if placeholder}
					<option value="" disabled>{placeholder}</option>
				{/if}
				{#each options as option}
					<option value={option.value}>{option.label}</option>
				{/each}
			</select>
		{:else if type === 'textarea'}
			<textarea
				{id}
				bind:value
				{placeholder}
				{disabled}
				{required}
				on:input={handleInput}
				on:change={handleChange}
				class="field-input textarea-input"
				class:loading
			></textarea>
		{:else if type === 'checkbox'}
			<label class="checkbox-wrapper">
				<input
					{id}
					type="checkbox"
					bind:checked={value}
					{disabled}
					{required}
					on:change={handleChange}
					class="checkbox-input"
				/>
				<span class="checkbox-label">{label}</span>
			</label>
		{:else if type === 'range'}
			<input
				{id}
				type="range"
				bind:value
				{disabled}
				{required}
				min={min}
				max={max}
				step={step}
				on:input={handleInput}
				on:change={handleChange}
				class="field-input range-input"
				style={"--range-progress: " + rangeProgress + "%"}
			/>
		{:else}
			<input
				{id}
				{type}
				bind:value
				{placeholder}
				{disabled}
				{required}
				{min}
				{max}
				{step}
				on:input={handleInput}
				on:change={handleChange}
				class="field-input text-input"
				class:loading
			/>
		{/if}
		
		<!-- Validation indicator -->
		<div class="validation-indicator">
			{#if isValidating}
				<div class="spinner"></div>
			{:else if isValid}
				<svg class="check-icon" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
				</svg>
			{:else if hasError}
				<svg class="error-icon" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
				</svg>
			{/if}
		</div>
	</div>
	
	{#if hasError}
		<div class="error-message">
			{error}
		</div>
	{:else if helpText}
		<div class="help-text">
			{helpText}
		</div>
	{/if}
	{#if failedMessage}
		<div class="inline-failed subtle">
			{failedMessage}
		</div>
	{/if}
</div>

<style>
	/* Allow native number spinners by removing suppression */
	input[type='number']::-webkit-outer-spin-button,
	input[type='number']::-webkit-inner-spin-button {
		-webkit-appearance: auto;
	}
	input[type='number'] {
		-moz-appearance: number-input;
	}
	/* Keep select arrows hidden */
	.select-input {
		cursor: pointer;
		-webkit-appearance: none;
		-moz-appearance: none;
		appearance: none;
		background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3e%3c/svg%3e");
		background-position: right 0.5rem center;
		background-repeat: no-repeat;
		background-size: 1.5em 1.5em;
		padding-right: 2.5rem;
	}
	
	/* Style range slider (brightness) */
	input[type='range'], .range-input {
		--track-height: 8px;
		-webkit-appearance: none;
		width: 100%;
		height: var(--track-height);
		background: linear-gradient(90deg, var(--color-primary, #3b82f6) 0%, var(--color-primary, #3b82f6) var(--range-progress, 0%), var(--color-border, #d1d5db) var(--range-progress, 0%), var(--color-border, #d1d5db) 100%);
		border-radius: 9999px;
		outline: none;
	}
	input[type='range']::-webkit-slider-thumb {
		-webkit-appearance: none;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: #ffffff;
		border: 2px solid var(--color-primary, #3b82f6);
		box-shadow: 0 1px 2px rgba(0,0,0,0.15);
		margin-top: calc((var(--track-height) - 18px) / 2); /* center thumb vertically */
	}
	input[type='range']::-moz-range-thumb {
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: #ffffff;
		border: 2px solid var(--color-primary, #3b82f6);
		box-shadow: 0 1px 2px rgba(0,0,0,0.15);
	}
	input[type='range']::-moz-range-progress {
		height: var(--track-height);
		background: var(--color-primary, #3b82f6);
		border-radius: 9999px;
	}
	input[type='range']::-moz-range-track {
		height: var(--track-height);
		background: var(--color-border, #d1d5db);
		border-radius: 9999px;
	}
	.form-field {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}
	
	.field-label {
		font-weight: 500;
		color: var(--color-text-primary, #374151);
		font-size: 0.875rem;
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}
	
	.required-indicator {
		color: var(--color-error, #ef4444);
		font-weight: bold;
	}
	
	.field-wrapper {
		position: relative;
		display: flex;
		align-items: center;
	}
	
	.field-input {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid var(--color-border, #d1d5db);
		border-radius: 0.375rem;
		font-size: 0.875rem;
		transition: all 0.2s ease;
		background: var(--color-surface, #ffffff);
		color: var(--color-text-primary, #374151);
	}
	
	.field-input:focus {
		outline: none;
		border-color: var(--color-primary, #3b82f6);
		box-shadow: 0 0 0 3px var(--color-primary-alpha, rgba(59, 130, 246, 0.1));
	}
	
	.field-input:disabled {
		background: var(--color-surface-disabled, #f9fafb);
		color: var(--color-text-disabled, #9ca3af);
		cursor: not-allowed;
	}
	
	.field-input.loading {
		background-image: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
		background-size: 200% 100%;
		animation: loading-shimmer 1.5s infinite;
	}
	
	.has-error .field-input {
		border-color: var(--color-error, #ef4444);
		box-shadow: 0 0 0 3px var(--color-error-alpha, rgba(239, 68, 68, 0.1));
	}
	
	.is-valid .field-input {
		border-color: var(--color-success, #10b981);
		box-shadow: 0 0 0 3px var(--color-success-alpha, rgba(16, 185, 129, 0.1));
	}
	
	.textarea-input {
		min-height: 4rem;
		resize: vertical;
	}
	
	.select-input {
		cursor: pointer;
		/* Hide native browser arrow */
		-webkit-appearance: none;
		-moz-appearance: none;
		appearance: none;
		/* Custom chevron icon */
		background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3e%3c/svg%3e");
		background-position: right 0.5rem center;
		background-repeat: no-repeat;
		background-size: 1.5em 1.5em;
		padding-right: 2.5rem;
	}
	
	.checkbox-wrapper {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
	}
	
	.checkbox-input {
		width: 1rem;
		height: 1rem;
		accent-color: var(--color-primary, #3b82f6);
	}
	
	.checkbox-label {
		font-size: 0.875rem;
		color: var(--color-text-primary, #374151);
	}
	
	.validation-indicator {
		position: absolute;
		right: 0.75rem;
		display: flex;
		align-items: center;
		pointer-events: none;
		opacity: 0.8;
		transition: opacity 150ms ease;
	}
	
	.spinner {
		width: 0.75rem; /* subtle */
		height: 0.75rem;
		border: 2px solid var(--color-border, #cbd5e1);
		border-top: 2px solid var(--color-primary, #60a5fa);
		border-radius: 50%;
		animation: spin 1.2s linear infinite; /* slightly slower */
	}
	
	.check-icon {
		width: 0.875rem; /* subtle */
		height: 0.875rem;
		color: var(--color-success, #10b981);
		opacity: 0.9;
	}
	
	.error-icon {
		width: 1rem;
		height: 1rem;
		color: var(--color-error, #ef4444);
	}
	
	.error-message {
		color: var(--color-error, #ef4444);
		font-size: 0.75rem;
		margin-top: 0.25rem;
	}
	
	.help-text {
		color: var(--color-text-secondary, #6b7280);
		font-size: 0.75rem;
		margin-top: 0.25rem;
	}
	
	@keyframes spin {
		0% { transform: rotate(0deg); }
		100% { transform: rotate(360deg); }
	}
	
	@keyframes loading-shimmer {
		0% { background-position: -200% 0; }
		100% { background-position: 200% 0; }
	}
	.inline-failed.subtle {
		color: var(--color-error, #ef4444);
		font-size: 0.75rem;
		margin-top: 0.15rem;
		opacity: 0.85;
	}
</style>