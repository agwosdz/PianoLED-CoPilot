# Canvas Renderer Testing Guide

## Quick Start

### Enable Canvas Renderer

1. Open Play page
2. Check the box: "Use Canvas Renderer (optimized for Pi Zero 2W)"
3. Load a MIDI file and press Play
4. Compare with DOM renderer by unchecking the box

## Performance Testing

### Desktop (Windows/Mac/Linux)

#### Using Chrome DevTools

1. **Open DevTools** (F12)
2. **Go to Performance tab**
3. **Click Record button**
4. **Start MIDI playback**
5. **Let it play for 10-30 seconds**
6. **Stop recording**

**What to look for**:
- **FPS**: Should be 50-60 FPS consistently
- **Frame time**: < 16ms per frame (1000ms / 60fps)
- **Render function**: Should be the main CPU time
- **Memory**: Compare heap snapshots before/after

#### Memory Comparison

1. **Open DevTools** → **Memory tab**
2. **Take heap snapshot** (DOM renderer active, 919 notes)
   - Look for: DOM nodes count should be ~1000+
   - Memory: ~50-100 MB
3. **Toggle to Canvas renderer**
4. **Take another heap snapshot**
   - Look for: DOM nodes count ~200
   - Memory: ~5-10 MB
5. **Compare**: Should see 80% reduction

#### Speed Benchmark

**Test 1: DOM Renderer**
1. Uncheck Canvas renderer
2. Load MIDI (919 notes)
3. Press Play and let run for 30 seconds
4. Record FPS in browser console:
   ```javascript
   // Copy this to console
   let frameCount = 0;
   let lastTime = performance.now();
   setInterval(() => {
     console.log(`FPS: ${frameCount}`);
     frameCount = 0;
   }, 1000);
   ```

**Test 2: Canvas Renderer**
1. Check Canvas renderer
2. Load same MIDI file
3. Play and measure FPS with same script
4. Compare results

**Expected Results**:
- DOM: 20-40 FPS (many divs to update)
- Canvas: 50-60 FPS (single element to render)

### Raspberry Pi Zero 2W

#### Prerequisites

```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Install dependencies if needed
sudo apt-get update
sudo apt-get install -y chromium-browser

# Check system resources
free -h              # Available memory
top -b -n 1         # CPU usage
```

#### Remote Testing

1. **On your PC**: Start port forwarding
   ```bash
   # Assuming Pi runs on :5000
   ssh -L 5000:localhost:5000 pi@raspberrypi.local
   ```

2. **On your browser**: Navigate to `http://localhost:5000/play`

3. **Load MIDI file** and test both renderers

#### Performance Monitoring on Pi

**Terminal 1** - Monitor resources:
```bash
watch -n 1 'free -h && echo "---" && top -b -n 1 | head -15'
```

**Terminal 2** - Check GPU usage:
```bash
# If available
vcgencmd get_mem gpu
vcgencmd measure_temp
```

**Browser Console** - Check FPS:
```javascript
let lastTime = performance.now();
let frameCount = 0;
function measureFPS() {
  frameCount++;
  const now = performance.now();
  if (now - lastTime >= 1000) {
    console.log(`FPS: ${frameCount}`);
    frameCount = 0;
    lastTime = now;
  }
  requestAnimationFrame(measureFPS);
}
measureFPS();
```

## Visual Testing Checklist

### Both Renderers Should Show

- [ ] Piano keyboard at bottom with all 88 keys
- [ ] White keys and black keys properly positioned
- [ ] Time grid lines across top (1 line per second)
- [ ] MIDI note bars at correct time positions
- [ ] MIDI note bars at correct key heights
- [ ] Colors match between renderers (pitch-based)
- [ ] Opacity of bars varies with velocity
- [ ] Current position (blue line) moves smoothly
- [ ] Play/Pause/Stop controls work
- [ ] Time display matches bar position

### Canvas-Specific

- [ ] Smooth rendering without jank
- [ ] No flickering during playback
- [ ] Bars appear correctly when scrolling
- [ ] Resize window and check canvas scales properly

### DOM-Specific (comparison)

- [ ] Same visual output as Canvas
- [ ] May see performance difference
- [ ] Check for layout thrashing in DevTools

## Comparison Metrics

### Create a Simple Benchmark

**Save as `benchmark-renderers.js`** in DevTools console:

```javascript
async function benchmarkRenderer(name, duration = 30000) {
  console.log(`\n=== Benchmarking ${name} ===`);
  
  // Measure memory
  if (performance.memory) {
    console.log(`Memory used: ${(performance.memory.usedJSHeapSize / 1048576).toFixed(2)} MB`);
  }
  
  // Measure FPS
  let frameCount = 0;
  let startTime = performance.now();
  let minFPS = 60;
  let maxFPS = 0;
  
  function countFrame() {
    frameCount++;
  }
  
  // Hook into requestAnimationFrame
  const startTimestamp = performance.now();
  let measurements = [];
  
  for (let i = 0; i < 60; i++) {  // Measure 60 frames
    measurements.push(frameCount);
    await new Promise(r => setTimeout(r, 16));  // 16ms = 60 FPS
  }
  
  console.log(`Average FPS: ${measurements.reduce((a,b)=>a+b)/measurements.length}`);
  console.log(`Min: ${Math.min(...measurements)}, Max: ${Math.max(...measurements)}`);
}

// Run after selecting renderer
console.log("1. Select DOM renderer, then run:");
console.log("benchmarkRenderer('DOM Renderer')");
console.log("\n2. Toggle to Canvas renderer, then run:");
console.log("benchmarkRenderer('Canvas Renderer')");
```

## Test Results Template

### DOM Renderer (Default)
```
Desktop Performance:
- FPS: [  ] frames per second
- Memory: [  ] MB
- Frame Time: [  ] ms average

Pi Zero 2W Performance:
- FPS: [  ] frames per second  
- CPU Usage: [  ] %
- Memory: [  ] MB
- Playback Smooth: [ ] Yes / [ ] No
```

### Canvas Renderer
```
Desktop Performance:
- FPS: [  ] frames per second
- Memory: [  ] MB
- Frame Time: [  ] ms average

Pi Zero 2W Performance:
- FPS: [  ] frames per second
- CPU Usage: [  ] %
- Memory: [  ] MB
- Playback Smooth: [ ] Yes / [ ] No
```

### Expected Results Summary
```
Improvement Factors:
- FPS Gain: [  ]% faster
- Memory Saved: [  ]%
- CPU Reduced: [  ]%
```

## Troubleshooting

### Canvas not rendering
1. Check browser console for errors
2. Verify Canvas 2D API support: 
   ```javascript
   !!document.createElement('canvas').getContext('2d')
   ```
3. Try toggling off and back on

### DOM renderer slower than expected
1. Close other browser tabs
2. Check for hardware acceleration settings
3. Try different browser (Chrome vs Firefox)

### Pi Zero 2W issues
1. Check memory: `free -h` (should have >200MB)
2. Verify Chromium is running (not X11)
3. Check CPU temp: `vcgencmd measure_temp`
4. Try killing background processes: `killall -9 python3 node`

### Visual differences between renderers
1. Note positions should match exactly
2. Colors might have slight variations (hex vs RGB)
3. Font rendering in time labels may differ slightly
4. This is expected and acceptable

## Next Steps After Testing

### If Canvas performs better (expected):
- [ ] Deploy Canvas renderer to production
- [ ] Consider removing DOM renderer code later
- [ ] Document performance improvements

### If performance is similar:
- [ ] Keep both options available
- [ ] Document findings
- [ ] Consider viewport culling optimization

### If issues found:
- [ ] Debug with browser DevTools
- [ ] Check Canvas API documentation
- [ ] File bug report with reproduction steps

## Resources

- **MDN Canvas API**: https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API
- **Chrome DevTools Performance**: https://developer.chrome.com/docs/devtools/performance/
- **Pi Zero 2W Hardware**: https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/

---

**Status**: Ready for testing on desktop and Pi Zero 2W
