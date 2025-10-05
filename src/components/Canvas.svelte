<script>
  import { onMount } from "svelte";
  import { Canvas, Image as FabricImage } from "fabric";
  import TreeView from "../lib/tree/TreeView.svelte";
  import { imagesRefresh } from "../stores/imagesRefresh.js";
  import Upload from "./Upload.svelte";

  let canvasEl;
  let fabricCanvas;

  // small incrementing id for objects so stack logs are useful
  let _nextObjectId = 1;

  // track whether an object is selected (for enabling toolbar buttons)
  let selectedExists = false;
  // when true, the next canvas click will convert the clicked object to the background
  let makeBgMode = false;

  // List of image URLs (returned from your backend)
  let images = [];
  let loading = true;
  let loadError = null;

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

        // assign a simple id so debugging / stack prints show something meaningful
        try {
          const assignedId = `img-${_nextObjectId++}`;
          // store on the object and in its properties for serialization
          fImg.set && fImg.set({ id: assignedId });
          fImg.id = assignedId;
        } catch (e) {
          /* ignore */
        }

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
        // ensure Fabric recalculates object coordinates for selection bounds
        try {
          fImg.setCoords && fImg.setCoords();
        } catch (e) {}
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
    console.log('handleDragOver', e);
  }
  function handleDrop(e) {
    e.preventDefault();

    // compute pointer in canvas coords
    // let pointer;
    // try {
    //   pointer = fabricCanvas.getPointer(e);
    // } catch (err) {
      const rect = canvasEl.getBoundingClientRect();
      let pointer = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    // }

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

    function changeBackgroundImage(imagePath, resize = false) {
    // imagePath: string (URL or relative path).
    // resize: boolean - if true, resize the Fabric canvas to match the image dimensions.
    if (!fabricCanvas) {
      console.warn('changeBackgroundImage: fabricCanvas not initialized yet');
      return;
    }

    const imgEl = new window.Image();
    // allow export/toDataURL without taint when possible
    imgEl.crossOrigin = 'anonymous';
    imgEl.onload = () => {
      try {
        // create a Fabric image from the loaded DOM image
        const bg = new FabricImage(imgEl, {
          originX: 'left',
          originY: 'top',
          left: 0,
          top: 0,
          selectable: false,
          evented: false,
        });

        // Per Fabric note: attach a reference to the canvas so the image can
        // detect zoom/viewport changes. Also disable objectCaching so the
        // background responds to zoom correctly.
        try {
          bg.canvas = fabricCanvas;
        } catch (e) {
          /* ignore if read-only */
        }
        bg.set({ objectCaching: false });

        // console.log("Set background image", bg);

        // Enforce maximum/minimum rules and decide how to size the canvas.
        // Max: 500W x 800H. Min: 300W x 500H. If image exceeds max, scale it
        // down to fit within max before any canvas resize. If image is below
        // min and resize=true we do NOT shrink the canvas (leave incomplete
        // background).
        const RAW_IW = imgEl.naturalWidth || imgEl.width || 1;
        const RAW_IH = imgEl.naturalHeight || imgEl.height || 1;
        const MAX_W = 500;
        const MAX_H = 800;
        const MIN_W = 300;
        const MIN_H = 500;

        // downscale factor to respect maximum constraints
        const downScaleForMax = Math.min(1, MAX_W / RAW_IW, MAX_H / RAW_IH);
        const iw = Math.max(1, Math.round(RAW_IW * downScaleForMax));
        const ih = Math.max(1, Math.round(RAW_IH * downScaleForMax));

        let cw = fabricCanvas.getWidth();
        let ch = fabricCanvas.getHeight();

        if (resize) {
          // If the (possibly downscaled) image is smaller than minimum, do
          // not shrink the canvas; leave the canvas size as-is and show an
          // "incomplete" background anchored at top-left. Otherwise resize
          // the canvas to the image size.
          if (iw < MIN_W || ih < MIN_H) {
            console.log('changeBackgroundImage: image smaller than minimum; skipping canvas shrink');
            // keep canvas size; cw/ch remain current
          } else {
            try {
              fabricCanvas.setWidth(iw);
              fabricCanvas.setHeight(ih);
              if (canvasEl) {
                canvasEl.width = iw;
                canvasEl.height = ih;
                // also update style so layout uses the new size
                canvasEl.style.width = `${iw}px`;
                canvasEl.style.height = `${ih}px`;
              }
              cw = iw;
              ch = ih;
            } catch (e) {
              console.warn('changeBackgroundImage: failed to resize canvas', e);
            }
          }
        }

        // Determine background image scale. If we've resized the canvas to
        // match the image, draw it at 1:1 (or at the precomputed downscale).
        if (resize && iw >= MIN_W && ih >= MIN_H) {
          // Image (possibly downscaled to fit MAX) is used 1:1 as canvas
          // size. Compute the effective scale relative to the original raw
          // image so the Fabric image renders at the expected size.
          const effectiveScale = downScaleForMax;
          bg.set({ scaleX: effectiveScale, scaleY: effectiveScale });
        } else {
          // Not resizing canvas: contain-fit the (possibly downscaled)
          // image inside the current canvas
          const scale = Math.min(cw / iw, ch / ih);
          bg.set({ scaleX: scale, scaleY: scale });
        }

        // Prefer the convenience API if present (different Fabric builds expose it differently)
        if (typeof fabricCanvas.setBackgroundImage === 'function') {
            console.log("Using setBackgroundImage API");
          // Pass width/height so Fabric can position/scale the background consistently
          fabricCanvas.setBackgroundImage(
            bg,
            () => fabricCanvas.requestRenderAll(),
            {
              originX: 'left',
              originY: 'top',
              left: 0,
              top: 0,
              // when resized we want the background to match pixel size; when
              // not resized we give the canvas size so Fabric can compute
              // consistent placement.
              width: cw,
              height: ch,
            },
          );
        } else {
            console.log("Using fallback backgroundImage assignment");
          // Fallback: directly set the property and request a render
          bg.set({ left: 0, top: 0, originX: 'left', originY: 'top' });
          fabricCanvas.backgroundImage = bg;
          fabricCanvas.requestRenderAll();
        }

      } catch (err) {
        console.error('changeBackgroundImage: failed to set background', err);
      }
    };
    imgEl.onerror = (err) => {
      console.error('changeBackgroundImage: failed to load image', imagePath, err);
    };
    imgEl.src = imagePath;
  }

    function clearCanvas() {
        fabricCanvas.clear();
        // fabricCanvas.setBackgroundColor('#ffffff', () => {
        fabricCanvas.requestRenderAll();
        // });
        selectedExists = false;
    }

  async function exportAsPDF() {
    if (!canvasEl) {
      console.warn('exportAsPDF: canvas element not found');
      return;
    }

    try {
      // ensure canvas render is up-to-date
      fabricCanvas.requestRenderAll();

      // get image data from the canvas
      const dataUrl = canvasEl.toDataURL('image/png');

      // Create a jsPDF instance sized to the canvas aspect ratio.
      // We'll use points (pt) units where 1 pt = 1/72 inch. jsPDF supports
      // 'px' unit in some builds but to be robust we'll compute A4 fallback
      // sizing while preserving aspect.
      const img = new Image();
      img.src = dataUrl;
      await new Promise((res, rej) => {
        img.onload = res;
        img.onerror = rej;
      });

      const cw = canvasEl.width || canvasEl.clientWidth || img.width;
      const ch = canvasEl.height || canvasEl.clientHeight || img.height;

      // Dynamically obtain jsPDF (avoid build-time peer dep issues).
      let jsPDFModule = null;
      try {
        jsPDFModule = await import('jspdf');
      } catch (e) {
        // If dynamic import fails (package not installed), attempt to load
        // the UMD build from jsDelivr and read window.jspdf
        await new Promise((resolve, reject) => {
          const existing = document.getElementById('jspdf-cdn');
          if (existing && window.jspdf) return resolve();
          const s = document.createElement('script');
          s.id = 'jspdf-cdn';
          s.src = 'https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js';
          s.onload = () => resolve();
          s.onerror = (err) => reject(err);
          document.head.appendChild(s);
        }).catch((err) => {
          console.warn('Could not load jsPDF dynamically, will fallback to image open', err);
        });
        jsPDFModule = window.jspdf ? window.jspdf : null;
      }

      if (!jsPDFModule) {
        throw new Error('jsPDF not available');
      }

      const jsPDFCtor = jsPDFModule.jsPDF || jsPDFModule.default || jsPDFModule;

      // Use jsPDF with 'portrait' or 'landscape' based on wider dimension
      const orientation = cw > ch ? 'landscape' : 'portrait';
      // Use mm units for more precise control
      const pdf = new jsPDFCtor({ orientation, unit: 'mm', format: 'a4' });

      // A4 dimensions in mm
      const A4_W = orientation === 'portrait' ? 210 : 297;
      const A4_H = orientation === 'portrait' ? 297 : 210;

      // Compute image size to fit A4 while preserving aspect ratio
      const scale = Math.min(A4_W / cw, A4_H / ch);
      const imgW = cw * scale;
      const imgH = ch * scale;
      const marginX = (A4_W - imgW) / 2;
      const marginY = (A4_H - imgH) / 2;

      // add image to PDF
      pdf.addImage(dataUrl, 'PNG', marginX, marginY, imgW, imgH);

      // trigger download
      pdf.save('canvas-export.pdf');
    } catch (err) {
      console.error('exportAsPDF failed:', err);
      // fallback: open image in new tab
      try {
        const dataUrl = canvasEl.toDataURL('image/png');
        const w = window.open('about:blank');
        if (w) w.document.write(`<img src="${dataUrl}" alt="canvas"/>`);
      } catch (err2) {
        console.error('fallback open image failed', err2);
      }
    }
  }

  // Export each object on the canvas as an individual PNG file.
  // This uses the canvas' toDataURL cropping options so we don't need to
  // clone objects into temporary Fabric canvases.
  async function exportAllObjectsAsPNGs() {
    if (!fabricCanvas) {
      console.warn('exportAllObjectsAsPNGs: fabricCanvas not initialized');
      return;
    }

    const objs = (fabricCanvas.getObjects && fabricCanvas.getObjects()) || [];
    if (!objs.length) {
      console.warn('exportAllObjectsAsPNGs: no objects to export');
      return;
    }

    // Save current active object so we can restore selection later.
    const prevActive = fabricCanvas.getActiveObject && fabricCanvas.getActiveObject();

    // Clear active selection so selection outlines don't show up in exports.
    try { fabricCanvas.discardActiveObject && fabricCanvas.discardActiveObject(); } catch (e) {}

    for (let i = 0; i < objs.length; i++) {
      const o = objs[i];
      // skip backgroundImage (it's not part of getObjects()) and invisible objects
      if (!o || o === fabricCanvas.backgroundImage || o.visible === false) continue;

      try {
        // get bounding rect in canvas coordinates (include stroke/transform)
        const rect = o.getBoundingRect && o.getBoundingRect(true);
        if (!rect) continue;
        const left = Math.max(0, Math.floor(rect.left));
        const top = Math.max(0, Math.floor(rect.top));
        const width = Math.max(1, Math.ceil(rect.width));
        const height = Math.max(1, Math.ceil(rect.height));

        // Ask Fabric to produce a cropped PNG for the bbox region
        const dataUrl = fabricCanvas.toDataURL
          ? fabricCanvas.toDataURL({ left, top, width, height, format: 'png' })
          : null;

        if (!dataUrl) {
          console.warn('exportAllObjectsAsPNGs: toDataURL not available for object', o);
          continue;
        }

        // Trigger download
        const a = document.createElement('a');
        a.href = dataUrl;
        const id = o.id || `object-${i + 1}`;
        a.download = `${id}.png`;
        // Some browsers require the anchor to be in the DOM
        document.body.appendChild(a);
        a.click();
        a.remove();

        // small delay to avoid overwhelming the browser with many downloads
        await new Promise((res) => setTimeout(res, 80));
      } catch (err) {
        console.warn('exportAllObjectsAsPNGs: failed for object', i, err);
      }
    }

    // Try to restore previous selection
    try {
      if (prevActive && fabricCanvas.setActiveObject) {
        fabricCanvas.setActiveObject(prevActive);
      }
    } catch (e) {
      /* ignore restore errors */
    }

    // ensure canvas re-renders and toolbar state is consistent
    try { selectedExists = !!(fabricCanvas.getActiveObject && fabricCanvas.getActiveObject()); } catch(e) {}
    fabricCanvas.requestRenderAll && fabricCanvas.requestRenderAll();
  }

  // Try to extract a usable image src (URL or dataURL) from a Fabric image object.
  function getObjectSrc(obj) {
    if (!obj) return null;
    try {
      if (typeof obj.getSrc === 'function') {
        const s = obj.getSrc();
        if (s) return s;
      }
    } catch (e) {}
    if (obj._originalElement && obj._originalElement.src) return obj._originalElement.src;
    if (obj._element && obj._element.src) return obj._element.src;
    try {
      if (typeof obj.getElement === 'function') {
        const el = obj.getElement();
        if (el && el.src) return el.src;
      }
    } catch (e) {}
    // last resort: if Fabric Image exposes toDataURL for the object itself
    try {
      if (obj.toDataURL) return obj.toDataURL();
    } catch (e) {}
    return null;
  }

  // Make the next-clicked object become the canvas background (and remove it).
  function make_background() {
    if (!fabricCanvas) {
      console.warn('make_background: fabricCanvas not initialized');
      return;
    }

    if (!canvasEl) {
      console.warn('make_background: canvas element not available');
      return;
    }

    makeBgMode = true;
    const prevCursor = canvasEl.style.cursor;
    canvasEl.style.cursor = 'crosshair';

    const handler = (e) => {
      try {
        const target = e.target || (e && e.subTargets && e.subTargets[0]) || null;
        if (!target) {
          console.log('make_background: no object clicked; cancelling');
          cleanup();
          return;
        }

        // if activeSelection, prefer the first member (user can convert grouped objects by ungrouping first)
        const obj = (target.type === 'activeSelection' && target._objects && target._objects[0]) ? target._objects[0] : target;

        const src = getObjectSrc(obj);
        if (!src) {
          // fallback: crop the object's bbox to a PNG dataURL and use that
          const rect = obj.getBoundingRect && obj.getBoundingRect(true);
          if (rect && fabricCanvas.toDataURL) {
            const left = Math.max(0, Math.floor(rect.left));
            const top = Math.max(0, Math.floor(rect.top));
            const width = Math.max(1, Math.ceil(rect.width));
            const height = Math.max(1, Math.ceil(rect.height));
            const dataUrl = fabricCanvas.toDataURL({ left, top, width, height, format: 'png' });
            if (dataUrl) {
              // remove the object then set background
              try { fabricCanvas.remove(obj); } catch (e) {}
              changeBackgroundImage(dataUrl, true);
            } else {
              console.warn('make_background: unable to generate data URL for object');
            }
          } else {
            console.warn('make_background: object has no source and cannot be exported');
          }
        } else {
          // remove object then set background image from its src
          try { fabricCanvas.remove(obj); } catch (e) {}
          changeBackgroundImage(src, true);
        }
      } catch (err) {
        console.error('make_background handler error:', err);
      } finally {
        cleanup();
      }
    };

    const cleanup = () => {
      makeBgMode = false;
      try { fabricCanvas.off && fabricCanvas.off('mouse:down', handler); } catch (e) {}
      try { canvasEl.style.cursor = prevCursor || 'crosshair'; } catch (e) {}
    };

    // attach a one-time mouse:down handler on the Fabric canvas
    try {
      fabricCanvas.on && fabricCanvas.on('mouse:down', handler);
    } catch (e) {
      console.warn('make_background: failed to attach mouse handler', e);
      // fallback: cancel mode
      cleanup();
    }
  }

  function bringForward() {
    const obj = fabricCanvas.getActiveObject();
    console.log("bringForward obj:", obj);
    if (!obj) return;
    try {
      const objs = fabricCanvas.getObjects();
      console.log('bring forward index:', objs.indexOf(obj));
      console.log('bring forward stack order:', objs.map((o,i)=>({i,type:o.type, id:o?.id})));

      // If ActiveSelection, move each member; otherwise move single object
      const members = (obj.type === 'activeSelection' && obj._objects) ? obj._objects.slice() : [obj];
      for (const o of members) {
        const idx = objs.indexOf(o);
        if (idx >= 0) {
          objs.splice(idx, 1);
          objs.push(o); // put at the end (top of visual stack)
        }
      }

      // Apply back to internal array (hacky but requested)
      try {
        fabricCanvas._objects = objs;
      } catch (e) {
        // Some Fabric builds may not allow direct assignment; try clearing and re-adding
        try {
          fabricCanvas.clear();
          for (const o of objs) fabricCanvas.add(o);
        } catch (e2) {
          console.warn('bringForward: failed to apply manual reorder', e2);
        }
      }

      // Update coords and render
      try { members.forEach(m => m.setCoords && m.setCoords()); } catch(e) {}
      fabricCanvas.requestRenderAll();
    } catch (err) {
      console.error('bringForward error:', err);
    }
  }

  function sendBackwards() {
    const obj = fabricCanvas.getActiveObject();
    console.log("sendBackwards obj:", obj);
    if (!obj) return;
    try {
      const objs = fabricCanvas.getObjects();
      console.log('sendBackwards index:', objs.indexOf(obj));
      console.log('sendBackwards stack order:', objs.map((o,i)=>({i,type:o.type, id:o?.id})));

      const members = (obj.type === 'activeSelection' && obj._objects) ? obj._objects.slice() : [obj];
      for (const o of members) {
        const idx = objs.indexOf(o);
        if (idx >= 0) {
          objs.splice(idx, 1);
          objs.unshift(o); // put at the front (bottom of visual stack)
        }
      }

      try {
        fabricCanvas._objects = objs;
      } catch (e) {
        try {
          fabricCanvas.clear();
          for (const o of objs) fabricCanvas.add(o);
        } catch (e2) {
          console.warn('sendBackwards: failed to apply manual reorder', e2);
        }
      }

      try { members.forEach(m => m.setCoords && m.setCoords()); } catch(e) {}
      // After sending objects to the back, clear the active selection so
      // the moved object doesn't remain selected (which in some builds
      // can cause it to be visually promoted again).
      try {
        if (fabricCanvas.discardActiveObject) {
          fabricCanvas.discardActiveObject();
        } else if (fabricCanvas.setActiveObject) {
          fabricCanvas.setActiveObject(null);
        }
      } catch (e) {
        console.warn('sendBackwards: failed to clear active object', e);
      }
      // Keep toolbar state in sync
      selectedExists = false;
      fabricCanvas.requestRenderAll();
    } catch (err) {
      console.error('sendBackwards error:', err);
    }
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

//   function resetCanvas() {
//     if (!fabricCanvas) return;

//     const DEF_W = 800;
//     const DEF_H = 600;

//     try {
//       // discard any active selection first
//       try { fabricCanvas.discardActiveObject && fabricCanvas.discardActiveObject(); } catch (e) {}

//       // clear objects/background
//       try { fabricCanvas.clear(); } catch (e) { console.warn('resetCanvas: clear failed', e); }
//       try { fabricCanvas.backgroundImage = null; } catch (e) {}

//       // reset viewport transform (important if canvas was zoomed/panned)
//       try { fabricCanvas.setViewportTransform && fabricCanvas.setViewportTransform([1, 0, 0, 1, 0, 0]); } catch (e) {}

//       // set logical Fabric canvas size
//       try {
//         fabricCanvas.setWidth(DEF_W);
//         fabricCanvas.setHeight(DEF_H);
//       } catch (e) {
//         console.warn('resetCanvas: setWidth/setHeight failed', e);
//       }

//       // sync DOM canvas size/style
//       if (canvasEl) {
//         try { canvasEl.style.width = `${DEF_W}px`; canvasEl.style.height = `${DEF_H}px`; } catch (e) {}
//         try { canvasEl.width = DEF_W; canvasEl.height = DEF_H; } catch (e) {}
//       }

//       // recalc offsets and object coords so selection boxes are correct
//       try { fabricCanvas.calcOffset && fabricCanvas.calcOffset(); } catch (e) {}
//       try { fabricCanvas.getObjects && fabricCanvas.getObjects().forEach(o => o.setCoords && o.setCoords()); } catch (e) {}

//       // update component state and render
//       canvasWidth = DEF_W;
//       canvasHeight = DEF_H;
//       selectedExists = false;
//       try { fabricCanvas.requestRenderAll && fabricCanvas.requestRenderAll(); } catch (e) {}
//     } catch (err) {
//       console.error('resetCanvas failed', err);
//     }
//   }

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
  let networkTestResult = null;

  async function runNetworkTest() {
    networkTestResult = 'Testing...';
    try {
      const r = await fetch('/all_images');
      if (!r.ok) throw new Error(`status ${r.status}`);
      const j = await r.json();
      networkTestResult = `OK: ${Array.isArray(j.images) ? j.images.length : '?.?'} images`;
    } catch (err) {
      networkTestResult = `ERR: ${err && err.message ? err.message : String(err)}`;
    }
  }

  async function loadImages() {
    loading = true;
    loadError = null;
    try {
  // Use a relative URL so the Vite dev server proxy (configured in vite.config.js)
  // forwards the request to the backend. Hard-coded localhost breaks when the
  // page is opened from another device (e.g. an iPad) because `localhost` then
  // refers to that device, not your dev machine.
  const response = await fetch('/all_images');
  if (!response.ok) throw new Error(`Fetch /all_images failed: ${response.status} ${response.statusText}`);
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
            img.onerror = (e) => reject(new Error(`Image load failed for ${url}`));
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
      loadError = err && err.message ? err.message : String(err);
    } finally {
      loading = false;
    }
  }
  let canvasWidth = 800;
  let canvasHeight = 600;
  onMount(() => {
    fabricCanvas = new Canvas(canvasEl, {
      width: canvasWidth,
      height: canvasHeight,
      backgroundColor: "transparent",
    });

    // ensure Fabric has correct offsets and is fully rendered
    try { fabricCanvas.calcOffset && fabricCanvas.calcOffset(); } catch(e) {}
    fabricCanvas.renderAll();

    // console.log('Fabric canvas initialized', fabricCanvas);
    // console.log("front method: ", fabricCanvas.sendObjectToBack);

    // console.log('Fabric canvas initialized', fabricCanvas);
    // console.log("front method: ", fabricCanvas.sendObjectToBack);

    // initial load
    loadImages();

    // subscribe to explicit refresh triggers
    _refreshUnsub = imagesRefresh.subscribe((n) => {
      // whenever the counter increments, reload images
      loadImages();
    });

    // images/sam_shapes/IMG_0430_L/mask_002_rgba.png

    // changeBackgroundImage('../../backend/images/sam_shapes/text_boxes.png', true);

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
      selectedExists = true;
      try {
        console.log('selection:created target:', obj);
        if (obj) {
          // ensure coords are up-to-date
          obj.setCoords && obj.setCoords();
          const rect = obj.getBoundingRect(true);
          console.log('boundingRect (contain=true):', rect);
          console.log('scaled size:', obj.getScaledWidth && obj.getScaledWidth(), obj.getScaledHeight && obj.getScaledHeight());
        }
      } catch (err) {
        console.warn('selection:created diagnostics failed', err);
      }
      fabricCanvas.requestRenderAll();
    });

    fabricCanvas.on("selection:updated", (e) => {
      const obj = e.target;
      selectedExists = true;
      try {
        console.log('selection:updated target:', obj);
        if (obj) {
          obj.setCoords && obj.setCoords();
          const rect = obj.getBoundingRect(true);
          console.log('boundingRect (contain=true):', rect);
          console.log('scaled size:', obj.getScaledWidth && obj.getScaledWidth(), obj.getScaledHeight && obj.getScaledHeight());
        }
      } catch (err) {
        console.warn('selection:updated diagnostics failed', err);
      }
      fabricCanvas.requestRenderAll();
    });

    fabricCanvas.on("selection:cleared", () => {
      selectedExists = false;
    });
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
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              d="M21 12a9 9 0 10-2.7 6.3"
              stroke="#bdae93"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <path
              d="M21 3v6h-6"
              stroke="#bdae93"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
        <button on:click={runNetworkTest} style="margin-left:8px;padding:6px 10px">Network test</button>
        {#if networkTestResult}
          <div style="font-size:0.9rem;margin-left:8px;color:var(--gb-muted)">{networkTestResult}</div>
        {/if}
      </div>
      <div style="display:flex;flex-direction:column;gap:8px">
        {#if loading}
          <div aria-live="polite">Loading images…</div>
        {:else}
          {#if loadError}
            <div style="color:salmon">Failed to load images: {loadError}</div>
          {/if}
        {/if}

        <!-- Always render the TreeView so it's present on small screens even when
             loading or when there are no images. This prevents the tree area from
             disappearing on iPad where touch navigation can hide content. -->
        <TreeView
          items={images}
          on:drag={(e) => onTreeDrag(e)}
          on:open={(e) => onTreeOpen(e)}
        />
      </div>
    </div>
    <div class="toolbar" role="toolbar" aria-label="Object actions">
      <button
        class="tool-btn"
        type="button"
        on:click={bringForward}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <title>Bring to front</title>
          <rect x="3.5" y="8.5" width="9" height="6" rx="1" transform="rotate(-6 3.5 8.5)" />
          <rect x="6" y="5" width="9" height="6" rx="1" transform="rotate(-3 6 5)" />
          <rect x="9" y="1.5" width="9" height="6" rx="1" />
          <path d="M17 22v-6" />
          <path d="M14 9l3-3 3 3" transform="translate(-3 9) scale(.67)"/>
        </svg>
        Bring to front
      </button>
      <button
        class="tool-btn"
        type="button"
        on:click={sendBackwards}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <title>Send back</title>
          <rect x="4" y="6" width="12" height="10" rx="1" />
          <path d="M19 7v4" />
          <path d="M16 14l3 3 3-3" transform="translate(-5 -3) scale(.6)"/>
        </svg>
        Send back
        </button>
      <button
        class="tool-btn"
        type="button"
        on:click={deleteActive}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <title>Delete</title>
          <rect x="6" y="7" width="12" height="12" rx="1" />
          <path d="M4 7h16" />
          <path d="M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2" />
          <path d="M10 11v6" />
          <path d="M14 11v6" />
        </svg>
        Delete
      </button>
      <button
        class="tool-btn"
        type="button"
        on:click={exportAsPDF}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <title>Convert to PDF</title>
        </svg>
        Convert to PDF
      </button>
      <button
        class="tool-btn"
        type="button"
        on:click={exportAllObjectsAsPNGs}
        title="Download all objects as PNGs">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <title>Download all objects</title>
          <path d="M21 15v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-4" />
          <path d="M7 10l5-5 5 5" />
          <path d="M12 5v10" />
        </svg>
        Download objects
      </button>
      <button
        class="tool-btn"
        type="button"
        on:click={make_background}
        title="Click an object to make it the background">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <title>Make background</title>
          <rect x="3" y="3" width="18" height="14" rx="1" />
          <path d="M3 18h18v3H3z" />
          <circle cx="8" cy="9" r="2" />
          <path d="M14 7l4 4" />
        </svg>
        Make background
      </button>
      <button
        class="tool-btn"
        type="button"
        on:click={clearCanvas}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <title>Clear Canvas</title>
        </svg>
        Clear Canvas
      </button>
      <!-- <button
        class="tool-btn"
        type="button"
        on:click={resetCanvas}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <title>Reset Canvas</title>
        </svg>
        Reset Canvas
      </button> -->
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
      width={canvasWidth}
      height={canvasHeight}
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

  .toolbar {
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
    color: var(--gb-bg);
    border-radius: 6px;
    padding: 1rem;
    box-shadow: none;
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

  /* Responsive: on small screens (tablets/phones) stack the tools above the canvas */
  @media (max-width: 900px) {
    .editor-container {
      flex-direction: column;
      height: auto;
    }
    .tools {
      width: 100%;
      height: auto;
      border-right: none;
      border-bottom: 1px solid var(--gb-border);
    }
    .canvas-container {
      width: 100%;
      padding: 12px 0;
    }
    canvas {
      width: calc(100% - 24px);
      max-width: 100%;
      height: auto !important;
    }
  }

  canvas {
    border: 1px solid var(--gb-border);
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
