import { writable, type Writable } from 'svelte/store';

// Type definitions
interface HistoryEntry {
	state: any;
	description: string;
	timestamp: number;
}

interface HistoryState {
	history: HistoryEntry[];
	currentIndex: number;
	maxHistorySize: number;
}

interface StateInfo {
	description: string;
	timestamp: number;
	index: number;
	total: number;
}

interface HistoryStore extends Writable<HistoryState> {
	pushState: (state: any, description: string) => void;
	undo: () => HistoryEntry | null;
	redo: () => HistoryEntry | null;
	canUndo: () => boolean;
	canRedo: () => boolean;
	clear: () => void;
	getCurrentStateInfo: () => StateInfo | null;
}

type UndoCallback = (state: any, description: string) => void;
type RedoCallback = (state: any, description: string) => void;

// History store for undo/redo functionality
function createHistoryStore(): HistoryStore {
	const { subscribe, set, update } = writable<HistoryState>({
		history: [],
		currentIndex: -1,
		maxHistorySize: 50
	});

	return {
		subscribe,
		set: (value: HistoryState) => set(value),
		update: (updater: (value: HistoryState) => HistoryState) => update(updater),
		
		// Add a new state to history
		pushState: (state: any, description: string): void => {
			update((store: HistoryState) => {
				// Remove any future states if we're not at the end
				if (store.currentIndex < store.history.length - 1) {
					store.history = store.history.slice(0, store.currentIndex + 1);
				}
				
				// Add new state
				store.history.push({
					state: JSON.parse(JSON.stringify(state)), // Deep clone
					description,
					timestamp: Date.now()
				});
				
				// Maintain max history size
				if (store.history.length > store.maxHistorySize) {
					store.history.shift();
				} else {
					store.currentIndex++;
				}
				
				return store;
			});
		},
		
		// Undo to previous state
		undo: (): HistoryEntry | null => {
			let undoState: HistoryEntry | null = null;
			update((store: HistoryState) => {
				if (store.currentIndex > 0) {
					store.currentIndex--;
					undoState = store.history[store.currentIndex];
				}
				return store;
			});
			return undoState;
		},
		
		// Redo to next state
		redo: (): HistoryEntry | null => {
			let redoState: HistoryEntry | null = null;
			update((store: HistoryState) => {
				if (store.currentIndex < store.history.length - 1) {
					store.currentIndex++;
					redoState = store.history[store.currentIndex];
				}
				return store;
			});
			return redoState;
		},
		
		// Check if undo is available
		canUndo: (): boolean => {
			let canUndo = false;
			update((store: HistoryState) => {
				canUndo = store.currentIndex > 0;
				return store;
			});
			return canUndo;
		},
		
		// Check if redo is available
		canRedo: (): boolean => {
			let canRedo = false;
			update((store: HistoryState) => {
				canRedo = store.currentIndex < store.history.length - 1;
				return store;
			});
			return canRedo;
		},
		
		// Clear history
		clear: (): void => {
			set({
				history: [],
				currentIndex: -1,
				maxHistorySize: 50
			});
		},
		
		// Get current state info
		getCurrentStateInfo: (): StateInfo | null => {
			let info: StateInfo | null = null;
			update((store: HistoryState) => {
				if (store.currentIndex >= 0 && store.currentIndex < store.history.length) {
					info = {
						description: store.history[store.currentIndex].description,
						timestamp: store.history[store.currentIndex].timestamp,
						index: store.currentIndex,
						total: store.history.length
					};
				}
				return store;
			});
			return info;
		}
	};
}

export const historyStore: HistoryStore = createHistoryStore();

// Keyboard shortcut handler
export function setupHistoryKeyboardShortcuts(
	undoCallback?: UndoCallback, 
	redoCallback?: RedoCallback
): () => void {
	function handleKeydown(event: KeyboardEvent): void {
		// Ctrl+Z or Cmd+Z for undo
		if ((event.ctrlKey || event.metaKey) && event.key === 'z' && !event.shiftKey) {
			event.preventDefault();
			const undoState = historyStore.undo();
			if (undoState && undoCallback) {
				undoCallback(undoState.state, undoState.description);
			}
		}
		
		// Ctrl+Shift+Z or Cmd+Shift+Z for redo
		if ((event.ctrlKey || event.metaKey) && event.key === 'z' && event.shiftKey) {
			event.preventDefault();
			const redoState = historyStore.redo();
			if (redoState && redoCallback) {
				redoCallback(redoState.state, redoState.description);
			}
		}
		
		// Ctrl+Y or Cmd+Y for redo (alternative)
		if ((event.ctrlKey || event.metaKey) && event.key === 'y') {
			event.preventDefault();
			const redoState = historyStore.redo();
			if (redoState && redoCallback) {
				redoCallback(redoState.state, redoState.description);
			}
		}
	}
	
	document.addEventListener('keydown', handleKeydown);
	
	// Return cleanup function
	return (): void => {
		document.removeEventListener('keydown', handleKeydown);
	};
}