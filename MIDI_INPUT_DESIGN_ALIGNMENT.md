# MIDI Input Section - Design Alignment with Listen Page

## Status
✅ **COMPLETE** - Play page MIDI input section now matches Listen page's design system

## Design Changes Applied

### Color Palette
| Element | Before | After |
|---------|--------|-------|
| Connected Badge | `#d1fae5` bg | `#f0fdf4` bg (deeper green) |
| Disconnected Badge | `#fee2e2` bg | `#fef2f2` bg (lighter red) |
| Error Background | `#fef2f2` + border | `#fee2e2` solid (matches disconnect button) |
| Toggle Input Color | browser default | `#0f172a` accent-color |

### Spacing & Typography

#### Label (midi-input-label)
- **Gap**: `0.5rem` → `0.75rem` (more breathing room)
- **User Select**: Added `user-select: none`

#### Toggle Input (midi-toggle-input)
- **Size**: `1.1rem` → `1.25rem` (slightly larger)
- **Accent Color**: Added `#0f172a` for consistent dark theme

#### Toggle Label (midi-toggle-label)
- **Weight**: Same `500`
- **Color**: Changed `#1e293b` → `#1f2937` (slightly warmer)

#### Status Badge (midi-status)
- **Font Size**: `0.9rem` → `0.875rem`
- **Padding**: `0.4rem 0.8rem` → `0.4rem 0.75rem`
- **Border Radius**: `6px` → `0.375rem` (more subtle)
- **Weight**: Kept `600`

### Device Selector Section

#### Container (midi-device-selector)
- **Removed**: White background + border box styling
- **Now**: Uses natural flex layout (cleaner, less boxed-in look)
- **Gap**: Changed to `0.5rem`

#### Row (device-selector-row)
- **Layout**: Uses `space-between` alignment
- **Gap**: `1rem` → `0.75rem`
- **Flex Wrap**: Removed (maintains alignment)

#### Label
- **Font Size**: `0.9rem` → `0.875rem`
- **Color**: `#1e293b` → `#1f2937`

### Buttons

#### Refresh Button (refresh-button)
- **Padding**: `0.5rem 1rem` → `0.4rem 0.75rem` (smaller, more refined)
- **Font Size**: `0.85rem` → `0.8rem`
- **Background**: `#f1f5f9` → `#f8fafc`
- **Border Radius**: `6px` → `0.375rem`
- **Hover State**: 
  - Old: `#e2e8f0` bg
  - New: `#ffffff` bg + `0 0 0 2px rgba(15, 23, 42, 0.1)` shadow
- **Border on Hover**: Now `#0f172a` (darker)
- **Active State**: Added `scale(0.95)` transform

#### Device Dropdown (device-dropdown)
- **Width**: `100%` → now responsive
- **Padding**: `0.6rem 0.8rem` → `0.625rem 0.875rem`
- **Border Radius**: `6px` → `0.375rem`
- **Focus State**: 
  - Old: `2px solid #2563eb` outline
  - New: `0 0 0 3px rgba(15, 23, 42, 0.1)` box-shadow (subtle, matches Listen)
- **Hover State**: Added `0 0 0 3px rgba(15, 23, 42, 0.05)` shadow
- **Disabled State**: 
  - Background: `#f8fafc`
  - Color: `#94a3b8`

#### Disconnect Button (disconnect-button)
- **Padding**: `0.6rem 1.2rem` → `0.5rem 0.875rem` (more compact)
- **Font Size**: `0.9rem` → `0.875rem`
- **Border Radius**: `6px` → `0.375rem`
- **Hover State**:
  - Old: `#fecaca` bg only
  - New: `#fca5a5` bg + `#dc2626` border + `#7f1d1d` text (more cohesive)
- **Active State**: Changed to `scale(0.95)` (matches refresh button)

### Error Message (midi-error)
- **Margin**: Removed top margin, set to `0`
- **Background**: `#fef2f2` → `#fee2e2` (matches disconnect button)
- **Color**: `#dc2626` → `#991b1b` (deeper red, more consistent)
- **Border**: Removed (`border: 1px solid #fecaca`)
- **Font Size**: `0.85rem` → `0.875rem`
- **Border Radius**: `6px` → `0.375rem`

## Visual Consistency Achieved

### Before
- **Feel**: Slightly different from Listen page, heavier shadows, more borders
- **Buttons**: Mixed button styles with different hover effects
- **Colors**: Some mismatched grays and reds
- **Spacing**: Slightly looser than Listen page

### After
- **Feel**: Matches Listen page exactly ✅
- **Buttons**: Consistent refined hover/active states
- **Colors**: Perfectly aligned with Listen page palette
- **Spacing**: Matches Listen page spacing system
- **Typography**: Consistent sizes and weights

## CSS Classes Updated

✅ `.midi-input-section`
✅ `.midi-input-header`
✅ `.midi-input-label`
✅ `.midi-toggle-input`
✅ `.midi-toggle-label`
✅ `.midi-status`
✅ `.midi-status.disconnected`
✅ `.midi-device-selector`
✅ `.device-selector-row`
✅ `.midi-device-selector label`
✅ `.refresh-button`
✅ `.refresh-button:hover:not(:disabled)`
✅ `.refresh-button:active:not(:disabled)`
✅ `.refresh-button:disabled`
✅ `.device-dropdown`
✅ `.device-dropdown:hover:not(:disabled)`
✅ `.device-dropdown:focus`
✅ `.device-dropdown:disabled`
✅ `.disconnect-button`
✅ `.disconnect-button:hover`
✅ `.disconnect-button:active`
✅ `.midi-error`

## Files Modified
- `frontend/src/routes/play/+page.svelte` - CSS styling (21 rules updated)

## Result
🎨 **Visual Harmony Achieved** - Play page now seamlessly matches Listen page design language

