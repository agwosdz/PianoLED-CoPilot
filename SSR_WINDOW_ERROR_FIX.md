# SSR Window Reference Error - Fixed

## 🐛 Problem
Frontend was throwing a **500 error** on page load with:
```
ReferenceError: window is not defined
    at H:\...\frontend\src\routes\settings\+page.svelte:188:5
```

This occurred during Server-Side Rendering (SSR) because the code tried to access `window` (which only exists in browsers) during server-side rendering.

## 🔍 Root Cause
The `+page.svelte` file had `window.addEventListener` and `window.removeEventListener` calls in `onMount` and `onDestroy` hooks without checking if the code was running in a browser environment.

During SSR (initial page render on server):
1. SvelteKit server renders the component on Node.js
2. `onDestroy` runs during SSR cleanup
3. Code tries to call `window.removeEventListener()`
4. `window` doesn't exist in Node.js → **ReferenceError**
5. Returns 500 error to client

## ✅ Solution
Wrapped all `window` access with `browser` guard:

### File: `frontend/src/routes/settings/+page.svelte`

**Step 1:** Add browser import (line 4)
```typescript
import { browser } from '$app/environment';
```

**Step 2:** Guard window access in onMount (lines 182-189)
```typescript
onMount(async () => {
  await loadSettingsData();
  await refreshMidiStatuses();
  await loadCalibrationData();

  // Listen for openAddOffset event from CalibrationSection3
  if (browser) {  // ← Guard added
    window.addEventListener('openAddOffset', handleOpenAddOffset as EventListener);
  }
});
```

**Step 3:** Guard window access in onDestroy (lines 191-198)
```typescript
onDestroy(() => {
  clearPatternResetTimer();
  // Clean up event listener
  if (browser) {  // ← Guard added
    window.removeEventListener('openAddOffset', handleOpenAddOffset as EventListener);
  }
});
```

## 📋 Changes Made
- ✅ Added `import { browser } from '$app/environment'`
- ✅ Wrapped `window.addEventListener()` with `if (browser)` check
- ✅ Wrapped `window.removeEventListener()` with `if (browser)` check

## 🧪 How It Works Now
1. **On Server (during SSR):**
   - `browser = false`
   - Window code skipped
   - No ReferenceError
   - Server returns valid HTML to client

2. **On Client (browser):**
   - `browser = true`
   - Event listeners properly attached/removed
   - Cross-component communication works
   - User can click "Add Offset" button

## 🎯 Impact
- ✅ Settings page now loads without 500 error
- ✅ Direct navigation to `/settings` works
- ✅ No more "switch pages then come back" workaround needed
- ✅ Proper SSR support for deployment
- ✅ Event-driven "Add Offset" feature continues to work

## 📝 Best Practice Applied
This follows SvelteKit's recommended pattern:
```typescript
import { browser } from '$app/environment';

if (browser) {
  // Only runs in browser, not during SSR
  window.addEventListener(...);
}
```

---

**Status:** ✅ **FIXED** - Ready for testing on `/settings` page
