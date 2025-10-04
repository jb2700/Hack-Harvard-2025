<script>
  import { onMount } from "svelte";
  import { Canvas, Image } from 'fabric';

  let canvasEl;
  let fabricCanvas;

  // track whether an object is selected (for enabling toolbar buttons)
  let selectedExists = false;

  // List of image URLs (returned from your backend)
  let images = [];

  // Load images list from backend
  async function fetchImages() {
    try {
      const resp = await fetch("http://localhost:5054/all_images");
      const data = await resp.json();
      // Assuming data.images is an array of filenames, e.g. ["foo.png", "bar.jpg"]
      images = data.images.map((name) => `http://localhost:5054${name}`);
    } catch (err) {
      console.error("Error fetching images:", err);
    }
  }

  // Add a new image object to the canvas (default position or specified)
  function addImageToCanvas(url, opts = {}) {
    // Load via an HTMLImageElement and construct a Fabric Image instance.
    // This avoids the deprecated Image.fromURL static helper.
    const imgEl = new window.Image();
    imgEl.crossOrigin = 'anonymous';
    imgEl.onload = () => {
      try {
        // Create Fabric image
        const fImg = new Image(imgEl, Object.assign({
          left: opts.left ?? 100,
          top: opts.top ?? 100,
          originX: 'center',
          originY: 'center',
          selectable: true,
          hasControls: true,
          hasBorders: true,
        }, opts));

        // If drag supplied a thumbnail display size, scale the Fabric image to match that display size
        if (opts.thumbSize && imgEl.naturalWidth && imgEl.naturalHeight) {
          const { w: thumbW, h: thumbH } = opts.thumbSize;
          // compute scale factors for width and height
          const scaleX = thumbW / imgEl.naturalWidth;
          const scaleY = thumbH / imgEl.naturalHeight;
          // choose uniform scale to preserve aspect ratio
          const scale = Math.min(scaleX || scaleY, scaleY || scaleX) || 1;
          fImg.scale(scale);
        }

        fabricCanvas.add(fImg);
        fabricCanvas.setActiveObject(fImg);
        fabricCanvas.requestRenderAll();
      } catch (err) {
        console.error('Error creating Fabric Image from element:', err);
      }
    };
    imgEl.onerror = (err) => {
      console.error('Failed to load image for canvas:', url, err);
    };
    imgEl.src = url;
  }

  // Helper used when user clicks a thumbnail (capture display size)
  function addFromThumbnail(e, url) {
    // find the image element inside the button (if any)
    let imgEl = null;
    if (e.currentTarget) imgEl = e.currentTarget.querySelector && e.currentTarget.querySelector('img');
    const thumbW = imgEl ? imgEl.clientWidth : undefined;
    const thumbH = imgEl ? imgEl.clientHeight : undefined;
    addImageToCanvas(url, { thumbSize: thumbW && thumbH ? { w: thumbW, h: thumbH } : undefined });
  }

  // Drag-and-drop handlers for thumbnails -> canvas
  function handleDragStart(e, url) {
    try {
      // set multiple types for wider browser compatibility
      e.dataTransfer.setData('text/plain', url);
      e.dataTransfer.setData('text/uri-list', url);
      // capture thumbnail element size so we can add the image to canvas at same display size
      let imgEl = null;
      if (e.target && e.target.tagName === 'IMG') imgEl = e.target;
      else if (e.currentTarget) imgEl = e.currentTarget.querySelector && e.currentTarget.querySelector('img');
      const thumbW = imgEl ? imgEl.clientWidth : 100;
      const thumbH = imgEl ? imgEl.clientHeight : 100;
      e.dataTransfer.setData('application/thumb-size', JSON.stringify({ w: thumbW, h: thumbH }));
      console.debug('dragstart set data:', url, { w: thumbW, h: thumbH });
      // create an offscreen canvas sized to the thumbnail to use as the drag image (so preview matches)
      try {
        const tmp = document.createElement('canvas');
        tmp.width = thumbW;
        tmp.height = thumbH;
        const ctx = tmp.getContext('2d');
        // draw the visible thumbnail into canvas (imgEl is loaded)
        if (imgEl) ctx.drawImage(imgEl, 0, 0, thumbW, thumbH);
        e.dataTransfer.setDragImage(tmp, Math.floor(thumbW / 2), Math.floor(thumbH / 2));
      } catch (err) {
        // fallback to native drag image
        const dragImg = new window.Image();
        dragImg.src = url;
        e.dataTransfer.setDragImage(dragImg, 30, 30);
      }
    } catch (err) {
      // fallback
      e.dataTransfer.setData('text/plain', url);
    }
  }

  function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }

  function handleDrop(e) {
    e.preventDefault();
    // try multiple types for compatibility
    const url = e.dataTransfer.getData('text/plain') || e.dataTransfer.getData('text/uri-list');
    console.debug('drop received:', url);
    if (!url) return;
    // try to read thumbnail size sent on dragstart
    let thumbSize = null;
    try {
      const raw = e.dataTransfer.getData('application/thumb-size');
      if (raw) thumbSize = JSON.parse(raw);
    } catch (err) { /* ignore */ }
    // Use Fabric's pointer translation so it accounts for canvas transforms/zoom
    let pointer;
    try {
      pointer = fabricCanvas.getPointer(e);
    } catch (err) {
      const rect = canvasEl.getBoundingClientRect();
      pointer = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }
    addImageToCanvas(url, { left: pointer.x, top: pointer.y, thumbSize });
  }

  // Toolbar actions
  function bringToFront() {
    const obj = fabricCanvas.getActiveObject();
    if (obj) {
      obj.bringToFront();
      fabricCanvas.requestRenderAll();
    }
  }

  function sendToBack() {
    const obj = fabricCanvas.getActiveObject();
    if (obj) {
      obj.sendToBack();
      fabricCanvas.requestRenderAll();
    }
  }

  function bringForward() {
    const obj = fabricCanvas.getActiveObject();
    if (obj) {
      obj.bringForward();
      fabricCanvas.requestRenderAll();
    }
  }

  function sendBackwards() {
    const obj = fabricCanvas.getActiveObject();
    if (obj) {
      obj.sendBackwards();
      fabricCanvas.requestRenderAll();
    }
  }

  function duplicateObject() {
    const obj = fabricCanvas.getActiveObject();
    if (!obj) return;
    obj.clone((cloned) => {
      cloned.set({ left: obj.left + 20, top: obj.top + 20 });
      fabricCanvas.add(cloned);
      fabricCanvas.setActiveObject(cloned);
      fabricCanvas.requestRenderAll();
    });
  }

  function deleteActive() {
    const obj = fabricCanvas.getActiveObject();
    if (obj) {
      fabricCanvas.remove(obj);
      fabricCanvas.requestRenderAll();
    }
  }

  onMount(async () => {
    // Initialize fabric canvas
    // Initialize Fabric.js canvas
    fabricCanvas = new Canvas(canvasEl, {
        width: 800,
        height: 600,
        backgroundColor: '#ffffff',
    });

    fabricCanvas.renderAll();
    // Fetch the images from backend
    await fetchImages();
    // Optionally add them initially:
    // images.forEach((url) => {
    //   // You could choose not to add all at once, but as user drags them
    //   // For demo, I'll add them:
    //   addImageToCanvas(url);
    // });

    // Handle delete key
    window.addEventListener("keydown", (e) => {
      if (e.key === "Delete" || e.key === "Backspace") {
        const obj = fabricCanvas.getActiveObject();
        if (obj) {
          fabricCanvas.remove(obj);
        }
      }
    });

    // Manage selection state and optionally bring a clicked object to front
    fabricCanvas.on("selection:created", (e) => {
      const obj = e.target;
      selectedExists = !!obj;
      if (obj) {
        // optionally bring selected to front so it's on top while editing
        // obj.bringToFront();
        fabricCanvas.requestRenderAll();
      }
    });

    fabricCanvas.on("selection:updated", (e) => {
      const obj = e.target;
      selectedExists = !!obj;
      if (obj) {
        // obj.bringToFront();
        fabricCanvas.requestRenderAll();
      }
    });

    fabricCanvas.on('selection:cleared', () => {
      selectedExists = false;
    });
  });
</script>

<style>
  .editor-container {
    display: flex;
    height: 100vh;
    align-items: center;
  }
  .tools {
    width: 200px;
    background-color: #f4f4f4;
    padding: 10px;
    border-right: 1px solid #ddd;
    align-self: center;
  }
  .toolbar {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 8px;
  }
  .tool-btn {
    font-size: 12px;
    padding: 6px 8px;
    border: 1px solid #ccc;
    background: white;
    cursor: pointer;
  }
  .tool-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .canvas-container {
    flex-grow: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: white;
    margin-left: 12px;
  }
  canvas {
    border: 1px solid #ccc;
  }
  .image-thumbnail {
    margin-bottom: 10px;
    cursor: pointer;
  }
  .image-thumbnail img {
    max-width: 100px;
    height: auto;
  }
</style>

<div class="editor-container">
  <div class="tools">
    <h3>Uploaded Images</h3>
    <div class="toolbar" role="toolbar" aria-label="Object actions">
      <button class="tool-btn" type="button" on:click={bringToFront} disabled={!selectedExists}>Bring to front</button>
      <button class="tool-btn" type="button" on:click={sendToBack} disabled={!selectedExists}>Send to back</button>
      <button class="tool-btn" type="button" on:click={bringForward} disabled={!selectedExists}>Bring forward</button>
      <button class="tool-btn" type="button" on:click={sendBackwards} disabled={!selectedExists}>Send back</button>
      <button class="tool-btn" type="button" on:click={duplicateObject} disabled={!selectedExists}>Duplicate</button>
      <button class="tool-btn" type="button" on:click={deleteActive} disabled={!selectedExists}>Delete</button>
    </div>
    {#each images as url}
      <!-- Use a button for accessibility (keyboard focus + click) and make it draggable on the image -->
      <button
        class="image-thumbnail"
        type="button"
        draggable="true"
        on:click={(e) => addFromThumbnail(e, url)}
        on:dragstart={(e) => { e.dataTransfer.effectAllowed = 'copy'; handleDragStart(e, url); }}
      >
        <img
          src={url}
          alt="Uploaded thumbnail"
          draggable="true"
          on:dragstart={(e) => { e.dataTransfer.effectAllowed = 'copy'; handleDragStart(e, url); }}
        />
      </button>
    {/each}
    <p>Click a thumbnail to add to canvas.</p>
  </div>

  <div class="canvas-container" role="application" aria-label="Canvas drop area" on:dragover={handleDragOver} on:drop={handleDrop}>
    <canvas
      bind:this={canvasEl}
      width="800"
      height="600"
      aria-label="Fabric editing canvas"
    ></canvas>
  </div>
</div>
