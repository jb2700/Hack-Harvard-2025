<script>
  import { onMount } from "svelte";
  import { Canvas, Image as FabricImage } from 'fabric';

  let canvasEl;
  let fabricCanvas;

  // track whether an object is selected (for enabling toolbar buttons)
  let selectedExists = false;

  // List of image URLs (returned from your backend)
  let images = [];
  let groups = [];
  let openGroups = {};


  // Add a new image object to the canvas (default position or specified)
  function addImageToCanvas(url, opts = {}) {
    // Load via an HTMLImageElement and construct a Fabric Image instance.
    // This avoids the deprecated Image.fromURL static helper.
    const imgEl = new window.Image();
    imgEl.crossOrigin = 'anonymous';
    imgEl.onload = () => {
      try {
        // Create Fabric image
        const fImg = new FabricImage(imgEl, Object.assign({
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
    fabricCanvas = new Canvas(canvasEl, {
        width: 500,
        height: 800,
        backgroundColor: '#ffffff',
    });

    fabricCanvas.renderAll();

    const response = await fetch('http://localhost:5054/all_images');
    console.log("Response:", response);
    const data = await response.json();
    console.log("Fetched image data:", data);
    console.log(data.images);
    const tempCanvas = document.createElement('canvas');
    const tempCtx = tempCanvas.getContext('2d');

    const loaded = await Promise.all(
      data.images.map(async (imagePath) => {
        const url = imagePath;
        const parts = imagePath.split('/').filter(Boolean);
        const filename = parts.length ? parts[parts.length - 1] : imagePath;
        const parent = parts.length > 1 ? parts[parts.length - 2] : '';
        const name = parent ? `${parent}/${filename}` : filename;

        // load the image (use window.Image to avoid shadowing the Fabric Image import)
        const img = new window.Image();
        img.crossOrigin = 'anonymous';
        img.src = url;

        await new Promise((resolve, reject) => {
          img.onload = () => resolve();
          img.onerror = (e) => reject(e);
        });

        // size the temp canvas to image natural size
        const iw = img.naturalWidth || img.width;
        const ih = img.naturalHeight || img.height;
        tempCanvas.width = iw;
        tempCanvas.height = ih;

        // draw and read pixels
        tempCtx.clearRect(0, 0, iw, ih);
        tempCtx.drawImage(img, 0, 0, iw, ih);
        const imageData = tempCtx.getImageData(0, 0, iw, ih).data;

        // find tight bbox of pixels with alpha > 0
        let minX = iw, minY = ih, maxX = -1, maxY = -1;
        for (let y = 0; y < ih; y++) {
          for (let x = 0; x < iw; x++) {
            const idx = (y * iw + x) * 4;
            const alpha = imageData[idx + 3];
            if (alpha > 0) {
              if (x < minX) minX = x;
              if (x > maxX) maxX = x;
              if (y < minY) minY = y;
              if (y > maxY) maxY = y;
            }
          }
        }

        // If fully transparent, fall back to full image bounds
        if (maxX === -1) {
          minX = 0; minY = 0; maxX = Math.max(0, iw - 1); maxY = Math.max(0, ih - 1);
        }

        const bbox = {
          x: minX,
          y: minY,
          width: maxX - minX + 1,
          height: maxY - minY + 1,
        };
        console.log(`Image ${name} bbox:`, bbox);

        // create a cropped image that contains ONLY the object bbox (full resolution)
        const cropCanvas = document.createElement('canvas');
        const cropCtx = cropCanvas.getContext('2d');
        // ensure at least 1x1
        const cropW = Math.max(1, bbox.width);
        const cropH = Math.max(1, bbox.height);
        cropCanvas.width = cropW;
        cropCanvas.height = cropH;
        // draw the image offset so the bbox region fills the crop canvas (this yields a full-resolution cropped image)
        cropCtx.clearRect(0, 0, cropCanvas.width, cropCanvas.height);
        cropCtx.drawImage(img, -bbox.x, -bbox.y, iw, ih);

        // This is the full-resolution cropped data URL (used as the actual image source for the canvas)
        const fullCroppedDataUrl = cropCanvas.toDataURL('image/png');

        // create a thumbnail DataURL for compact display in the sidebar (possibly scaled down)
        const maxThumb = 120; // max pixels on longest side for thumbnail
        let thumbDataUrl;
        if (Math.max(cropW, cropH) > maxThumb) {
          const scale = maxThumb / Math.max(cropW, cropH);
          const sw = Math.max(1, Math.round(cropW * scale));
          const sh = Math.max(1, Math.round(cropH * scale));
          const scaleCanvas = document.createElement('canvas');
          scaleCanvas.width = sw;
          scaleCanvas.height = sh;
          const sctx = scaleCanvas.getContext('2d');
          sctx.drawImage(cropCanvas, 0, 0, cropW, cropH, 0, 0, sw, sh);
          thumbDataUrl = scaleCanvas.toDataURL('image/png');
        } else {
          thumbDataUrl = fullCroppedDataUrl;
        }

        // Return the cropped full-resolution data URL as `url` so the canvas adds the minimal image.
        // naturalWidth/naturalHeight refer to the cropped region's original resolution.
        return { url: fullCroppedDataUrl, name, naturalWidth: cropW, naturalHeight: cropH, bbox, thumb: thumbDataUrl };
      })
    );

    images = loaded; // each item: { url, name, naturalWidth, naturalHeight, bbox, thumb }
    console.log("Fetched images with bbox:", images);

    // group images by the first path segment (folder), e.g. 'IMG_0430_L/mask_027_rgba.png'
    const groupsMap = new Map();
    images.forEach(img => {
      const parts = img.name.split('/').filter(Boolean);
      const groupName = parts.length > 1 ? parts[0] : '_ungrouped';
      if (!groupsMap.has(groupName)) groupsMap.set(groupName, []);
      groupsMap.get(groupName).push(img);
    });

    groups = Array.from(groupsMap.entries()).map(([groupName, items]) => ({ groupName, items }));
    // initialize open state (closed by default)
    openGroups = Object.fromEntries(groups.map(g => [g.groupName, false]));
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
  }

  .tools {
    width: 30vw;
    background-color: #f4f4f4;
    padding: 10px;
    border-right: 1px solid #ddd;
  }

  .canvas-container {
    width: 60vw;
    flex-grow: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: white;
  }

  canvas {
    border: 1px solid #ccc;
    cursor: crosshair;
  }

  .tool-button {
    margin-bottom: 10px;
    padding: 8px 16px;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    width: 100%;
  }

  .tool-button:hover {
    background-color: #0056b3;
  }

  .image-thumbnail {
    margin-bottom: 10px;
    text-align: center;
  }

  .image-thumbnail img {
    max-width: 100%;
    height: auto;
    cursor: pointer;
  }
</style>

<div class="editor-container">
  <div class="tools">
    <div class="toolbar" role="toolbar" aria-label="Object actions">
      <button class="tool-btn" type="button" on:click={bringToFront} disabled={!selectedExists}>Bring to front</button>
      <button class="tool-btn" type="button" on:click={sendToBack} disabled={!selectedExists}>Send to back</button>
      <button class="tool-btn" type="button" on:click={bringForward} disabled={!selectedExists}>Bring forward</button>
      <button class="tool-btn" type="button" on:click={sendBackwards} disabled={!selectedExists}>Send back</button>
      <button class="tool-btn" type="button" on:click={duplicateObject} disabled={!selectedExists}>Duplicate</button>
      <button class="tool-btn" type="button" on:click={deleteActive} disabled={!selectedExists}>Delete</button>
    </div>
    <h3>Uploaded Images</h3>
    {#each groups as group}
      <div>
        <button
          type="button"
          class="group-header"
          aria-expanded={openGroups[group.groupName]}
          on:click={() => { openGroups[group.groupName] = !openGroups[group.groupName]; openGroups = { ...openGroups }; }}
        >
          <strong>{group.groupName}</strong>
          <span class="count">{group.items.length}</span>
          <span class="caret">{openGroups[group.groupName] ? '▾' : '▸'}</span>
        </button>
        {#if openGroups[group.groupName]}
          <div class="group-items">
            {#each group.items as image}
              <button
                class="image-thumbnail"
                draggable="true"
                on:dragstart={(e) => handleDragStart(e, image.url)}
                aria-label={`Drag ${image.name} to canvas`}
                on:click={(e) => addFromThumbnail(e, image.url)}
              >
                <img src={image.thumb} alt={image.name} />
                <p>{image.name}</p>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    {/each}
  </div>

  <div class="canvas-container" role="application" aria-label="Canvas drop area" on:dragover={handleDragOver} on:drop={handleDrop}>
    <canvas
      bind:this={canvasEl}
      width="500"
      height="800"
      aria-label="Fabric editing canvas"
    ></canvas>
  </div>
</div>
