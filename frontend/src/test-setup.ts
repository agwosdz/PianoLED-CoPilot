import { vi } from 'vitest';
import '@testing-library/jest-dom';

// Configure environment for Svelte 5 client-side rendering
Object.defineProperty(globalThis, 'window', {
	value: global.window || {},
	writable: true
});

Object.defineProperty(globalThis, 'document', {
	value: global.document || {},
	writable: true
});

// Mock fetch globally for all tests
Object.defineProperty(window, 'fetch', {
	value: vi.fn(),
	writable: true
});

// Mock browser APIs for Svelte 5
Object.defineProperty(window, 'requestAnimationFrame', {
	value: vi.fn((cb) => setTimeout(cb, 16)),
	writable: true
});

Object.defineProperty(window, 'cancelAnimationFrame', {
	value: vi.fn(),
	writable: true
});

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
	observe: vi.fn(),
	unobserve: vi.fn(),
	disconnect: vi.fn()
}));

// Mock File and FileList for file upload tests
global.File = class MockFile {
	bits: any[];
	name: string;
	size: number;
	type: string;
	lastModified: number;
	webkitRelativePath: string = '';

	constructor(bits: any[], name: string, options: FilePropertyBag = {}) {
		this.bits = bits;
		this.name = name;
		this.size = options.lastModified || 0;
		this.type = options.type || '';
		this.lastModified = options.lastModified || Date.now();
	}

	stream(): ReadableStream<Uint8Array<ArrayBuffer>> {
		return new ReadableStream<Uint8Array<ArrayBuffer>>();
	}

	text(): Promise<string> {
		return Promise.resolve('');
	}

	arrayBuffer(): Promise<ArrayBuffer> {
		return Promise.resolve(new ArrayBuffer(0));
	}

	bytes(): Promise<Uint8Array<ArrayBuffer>> {
		return Promise.resolve(new Uint8Array(new ArrayBuffer(0)));
	}

	slice(start?: number, end?: number, contentType?: string): Blob {
		return new Blob();
	}
};

global.FileList = class MockFileList {
	length: number;
	[index: number]: File;

	constructor(files: File[] = []) {
		this.length = files.length;
		files.forEach((file, index) => {
			this[index] = file;
		});
	}

	item(index: number): File | null {
		return this[index] || null;
	}

	[Symbol.iterator](): ArrayIterator<File> {
		const files = Array.from({ length: this.length }, (_, i) => this[i]);
		return files[Symbol.iterator]();
	}
};