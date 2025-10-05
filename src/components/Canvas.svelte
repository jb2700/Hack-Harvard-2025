<script>
  import { onMount } from "svelte";
  import { Canvas, Image as FabricImage } from "fabric";
  import TreeView from "../lib/tree/TreeView.svelte";
  import { imagesRefresh } from "../stores/imagesRefresh.js";
  import Upload from "./Upload.svelte";

  let canvasEl;
  let fabricCanvas;

  // track whether an object is selected (for enabling toolbar buttons)
  let selectedExists = false;

  // List of image URLs (returned from your backend)
  let images = [];
  let loading = true;

  // Add a new image object to the canvas (default position or specified)
  function addImageToCanvas(url, opts = {}) {
    const imgEl = new window.Image();
    imgEl.crossOrigin = "anonymous";
    imgEl.onload = () => {
      try {
        const fImg = new FabricImage(
          imgEl,
          Object.assign(
            {
              left: opts.left ?? 100,
              top: opts.top ?? 100,
              originX: "center",
              originY: "center",
              selectable: true,
              hasControls: true,
              hasBorders: true,
            },
            opts,
          ),
        );

        if (opts.scale && typeof opts.scale === "number") {
          // modern Fabric uses scaleX/scaleY properties
          fImg.set({ scaleX: opts.scale, scaleY: opts.scale });
        } else if (
          opts.thumbSize &&
          imgEl.naturalWidth &&
          imgEl.naturalHeight
        ) {
          const { w: thumbW, h: thumbH } = opts.thumbSize;
          const scaleX = thumbW / imgEl.naturalWidth;
          const scaleY = thumbH / imgEl.naturalHeight;
          const scale = Math.min(scaleX || scaleY, scaleY || scaleX) || 1;
          fImg.set({ scaleX: scale, scaleY: scale });
        }

        fabricCanvas.add(fImg);
        fabricCanvas.setActiveObject(fImg);
        fabricCanvas.requestRenderAll();
      } catch (err) {
        console.error("Error creating Fabric Image from element:", err);
      }
    };
    imgEl.onerror = (err) => {
      console.error("Failed to load image for canvas:", url, err);
    };
    imgEl.src = url;
  }

  // Note: thumbnail click/drag helpers were removed in favor of TreeView/Folder drag handlers.

  function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }
  function handleDrop(e) {
    e.preventDefault();

    // compute pointer in canvas coords
    let pointer;
    try {
      pointer = fabricCanvas.getPointer(e);
    } catch (err) {
      const rect = canvasEl.getBoundingClientRect();
      pointer = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }

    // If a folder composite drag was started, the Folder component stored the structured payload
    // in a temporary global `window.__folderDragPayload` (set by onTreeDrag when the TreeView forwarded the folder drag).
    const folderPayload = window.__folderDragPayload || null;
    if (folderPayload && folderPayload.items && folderPayload.items.length) {
      const scale = folderPayload.scale || 1;
      const baseX = pointer.x;
      const baseY = pointer.y;
      // Place each child at relative position: pointer + (child.bbox - folder.bbox) * scale
      for (const child of folderPayload.items) {
        const cb = child.bbox || { x: 0, y: 0 };
        const fx = baseX + ((cb.x || 0) - (folderPayload.bbox?.x || 0)) * scale;
        const fy = baseY + ((cb.y || 0) - (folderPayload.bbox?.y || 0)) * scale;
        // child.url is expected to be the cropped full-resolution data URL
        addImageToCanvas(child.url, { left: fx, top: fy, scale });
      }
      // clear the temporary payload
      window.__folderDragPayload = null;
      return;
    }

    // Fallback: single-image drop
    const url =
      e.dataTransfer.getData("text/plain") ||
      e.dataTransfer.getData("text/uri-list");
    if (!url) return;
    let thumbSize = null;
    try {
      const raw = e.dataTransfer.getData("application/thumb-size");
      if (raw) thumbSize = JSON.parse(raw);
    } catch (err) {
      /* ignore */
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

  // Handlers for TreeView events
  function onTreeOpen(e) {
    const item = e.detail.item;
    // open = click: add image to canvas
    if (item && item.url) {
      addImageToCanvas(item.url, { thumbSize: { w: 100, h: 100 } });
    }
  }

  function onTreeDrag(e) {
    // e.detail.event is the original dragstart event
    const { event, item } = e.detail;
    // prepare dataTransfer similarly to handleDragStart
    try {
      if (item && item.type === "folder") {
        // stash the full folder payload for the eventual drop
        window.__folderDragPayload = item;
        // attach a minimal text fallback
        try {
          event.dataTransfer.setData(
            "text/plain",
            JSON.stringify({ type: "folder", name: item.name }),
          );
        } catch (_) {}
        // the Folder component already set application/folder-composite and drag image
      } else {
        const url = item.url;
        event.dataTransfer.setData("text/plain", url);
        event.dataTransfer.setData("text/uri-list", url);
        const thumbW = 100,
          thumbH = 100;
        event.dataTransfer.setData(
          "application/thumb-size",
          JSON.stringify({ w: thumbW, h: thumbH }),
        );
        const dragImg = new window.Image();
        dragImg.src = item.thumb || url;
        event.dataTransfer.setDragImage(dragImg, 30, 30);
      }
    } catch (err) {
      console.warn("onTreeDrag failed to set dataTransfer", err);
    }
  }

  function getBBox(imageData, iw, ih) {
    let minX = iw,
      minY = ih,
      maxX = 0,
      maxY = 0;
    for (let y = 0; y < ih; y++) {
      for (let x = 0; x < iw; x++) {
        const idx = (y * iw + x) * 4;
        const alpha = imageData[idx + 3];
        if (alpha > 0) {
          // non-transparent pixel
          if (x < minX) minX = x;
          if (x > maxX) maxX = x;
          if (y < minY) minY = y;
          if (y > maxY) maxY = y;
        }
      }
    }
    // Handle case where no non-transparent pixels found
    if (maxX < minX || maxY < minY) {
      return { x: 0, y: 0, width: 1, height: 1 };
    }
    return {
      x: minX,
      y: minY,
      width: maxX - minX + 1,
      height: maxY - minY + 1,
    };
  }

  let _refreshUnsub = null;

  async function loadImages() {
    loading = true;
    try {
      const response = await fetch("http://localhost:5054/all_images");
      const data = await response.json();
      const tempCanvas = document.createElement("canvas");
      const tempCtx = tempCanvas.getContext("2d");

      const loaded = await Promise.all(
        data.images.map(async (imagePath) => {
          const url = imagePath;
          const name = imagePath;

          const img = new window.Image();
          img.crossOrigin = "anonymous";
          img.src = url;

          await new Promise((resolve, reject) => {
            img.onload = () => resolve();
            img.onerror = (e) => reject(e);
          });

          const iw = img.naturalWidth || img.width;
          const ih = img.naturalHeight || img.height;
          tempCanvas.width = iw;
          tempCanvas.height = ih;

          tempCtx.clearRect(0, 0, iw, ih);
          tempCtx.drawImage(img, 0, 0, iw, ih);
          const imageData = tempCtx.getImageData(0, 0, iw, ih).data;

          const bbox = getBBox(imageData, iw, ih);

          const cropCanvas = document.createElement("canvas");
          const cropCtx = cropCanvas.getContext("2d");
          const cropW = Math.max(1, bbox.width);
          const cropH = Math.max(1, bbox.height);
          cropCanvas.width = cropW;
          cropCanvas.height = cropH;
          cropCtx.clearRect(0, 0, cropCanvas.width, cropCanvas.height);
          cropCtx.drawImage(img, -bbox.x, -bbox.y, iw, ih);

          const fullCroppedDataUrl = cropCanvas.toDataURL("image/png");

          const maxThumb = 120;
          let thumbDataUrl;
          if (Math.max(cropW, cropH) > maxThumb) {
            const scale = maxThumb / Math.max(cropW, cropH);
            const sw = Math.max(1, Math.round(cropW * scale));
            const sh = Math.max(1, Math.round(cropH * scale));
            const scaleCanvas = document.createElement("canvas");
            scaleCanvas.width = sw;
            scaleCanvas.height = sh;
            const sctx = scaleCanvas.getContext("2d");
            sctx.drawImage(cropCanvas, 0, 0, cropW, cropH, 0, 0, sw, sh);
            thumbDataUrl = scaleCanvas.toDataURL("image/png");
          } else {
            thumbDataUrl = fullCroppedDataUrl;
          }

          return {
            url: fullCroppedDataUrl,
            name,
            naturalWidth: cropW,
            naturalHeight: cropH,
            bbox,
            thumb: thumbDataUrl,
          };
        }),
      );

      images = loaded;
    } catch (err) {
      console.error("Failed to load images", err);
      images = [];
    } finally {
      loading = false;
    }
  }
  let canvasWidth = 1400;
  let canvasHeight = 1200;
  onMount(() => {
    fabricCanvas = new Canvas(canvasEl, {
      width: canvasWidth,
      height: canvasHeight,
      backgroundColor: "#1d2021",
    });

    fabricCanvas.renderAll();

    // initial load
    loadImages();

    // subscribe to explicit refresh triggers
    _refreshUnsub = imagesRefresh.subscribe((n) => {
      // whenever the counter increments, reload images
      loadImages();
    });

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
        fabricCanvas.requestRenderAll();
      }
    });

    fabricCanvas.on("selection:updated", (e) => {
      const obj = e.target;
      selectedExists = !!obj;
      if (obj) {
        fabricCanvas.requestRenderAll();
      }
    });

    fabricCanvas.on("selection:cleared", () => {
      selectedExists = false;
    });

    return () => {
      if (_refreshUnsub) _refreshUnsub();
    };
  });
</script>

<div class="editor-container">
  <div class="tools">
    <div class="top">
      <div style="display:flex;align-items:center;gap:8px">
        <Upload />
        <h3 class="toolbar-title">Uploaded Images</h3>
        <button
          title="Reload images"
          aria-label="Reload images"
          on:click={() => imagesRefresh.update((n) => n + 1)}
          style="background:none;border:0;padding:4px;cursor:pointer"
        >
          <!-- small reload SVG -->
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              d="M21 12a9 9 0 10-2.7 6.3"
              stroke="#333"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <path
              d="M21 3v6h-6"
              stroke="#333"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
      </div>
      {#if loading}
        <div>Loading images…</div>
      {:else}
        <TreeView
          items={images}
          on:drag={(e) => onTreeDrag(e)}
          on:open={(e) => onTreeOpen(e)}
        />
      {/if}
    </div>
    <div class="toolbar" role="toolbar" aria-label="Object actions">
      <button
        class="tool-btn"
        type="button"
        on:click={bringToFront}
        disabled={!selectedExists}>Bring to front</button
      >
      <button
        class="tool-btn"
        type="button"
        on:click={sendToBack}
        disabled={!selectedExists}>Send to back</button
      >
      <button
        class="tool-btn"
        type="button"
        on:click={bringForward}
        disabled={!selectedExists}>Bring forward</button
      >
      <button
        class="tool-btn"
        type="button"
        on:click={sendBackwards}
        disabled={!selectedExists}>Send back</button
      >
      <button
        class="tool-btn"
        type="button"
        on:click={duplicateObject}
        disabled={!selectedExists}>Duplicate</button
      >
      <button
        class="tool-btn"
        type="button"
        on:click={deleteActive}
        disabled={!selectedExists}>Delete</button
      >
    </div>
  </div>

  <div
    class="canvas-container"
    role="application"
    aria-label="Canvas drop area"
    on:dragover={handleDragOver}
    on:drop={handleDrop}
  >
    <canvas
      bind:this={canvasEl}
      width='${canvasWidth}'
      height='${canvasHeight}'
      aria-label="Fabric editing canvas"
    ></canvas>
  </div>
</div>

<style>
  /* Gruvbox-inspired theme variables */
  .editor-container {
    display: flex;
    height: 100vh;
    background: var(--gb-bg);
    color: var(--gb-text);
  }
  .toolbar-title {
    font-size: 1.8rem;
    font-weight: 600;
    color: var(--gb-muted);
    margin: 0;
  }

  .tools {
    width: 30vw;
    background-color: var(--gb-panel);
    padding: 12px;
    border-right: 1px solid var(--gb-border);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 10px;
    height: 80vh;
  }

  .canvas-container {
    display: flex;
    justify-content: center;
    align-items: center;
  }

  canvas {
    border: 2px solid var(--gb-canvas-edge);
    cursor: crosshair;
  }

  .top {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .toolbar-title {
    font-weight: 600;
    color: var(--gb-muted);
    margin: 0;
  }

  .bottom .toolbar {
    background: var(--gb-panel-variant);
    padding: 8px;
    border-radius: 6px;
    border: 1px solid var(--gb-border);
  }

  /*.tool-btn {
    margin-bottom: 10px;
    padding: 8px 12px;
    background-color: var(--gb-button);
    color: var(--gb-text);
    border: 1px solid var(--gb-border);
    border-radius: 6px;
    cursor: pointer;
    width: 100%;
    text-align: left;
  } */

  .tool-btn {
    background-color: var(--gb-muted);
  }
  .tool-btn:hover {
    background-color: var(--gb-button-hover);
  }

  /* Reload icon style */
  /* button[title="Reload images"] svg path { stroke: var(--gb-text); } */

  /* thumbnails and folder outlines */
  /* :global(.thumb) { width: 48px; height: auto; border: 1px solid var(--gb-border); background: var(--gb-panel-variant); border-radius:4px }
  :global(.composite-thumb) { width: 56px; height: 56px; object-fit: contain; border: 1px solid var(--gb-border); margin-left: auto; background: var(--gb-panel-variant); border-radius:4px } */

  /* Tree / folder visuals */
  :global(.folder) {
    color: var(--gb-text);
    border-bottom: 1px solid rgba(0, 0, 0, 0.12);
    padding-bottom: 6px;
    margin-bottom: 6px;
  }

  /* file entries wrapping */
  /* :global(.file-entries) { display:flex; flex-wrap:wrap; gap:8px } */

  /* small helpers */

  .editor-container {
    display: flex;
    height: 100vh;
  }

  .canvas-container {
    width: 80vw;
    flex-grow: 1;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  canvas {
    border: 1px solid #ccc;
    cursor: crosshair;
  }

  /* .tool-btn {
    margin-bottom: 10px;
    padding: 8px 16px;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    width: 100%;
  }

  .tool-btn:hover {
    background-color: #0056b3;
  } */

  /* removed unused .image-thumbnail and .tool-button styles */
</style>
