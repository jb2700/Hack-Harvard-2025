<script>
  import { onMount } from 'svelte';

  let canvas;
  let ctx;
  let images = [];
  let groups = [];
  let openGroups = {};
  let placedImages = [];
  let image_height;
  let image_width;

  function drawObject(index) {
        imgObj = placedImages[index];
        const img = new Image();
        img.src = imgObj.url;
        img.onload = () => {
        ctx.drawImage(img, imgObj.x, imgObj.y, imgObj.width, imgObj.height);
        // If this image is selected, draw border
        if (idx === selectedIndex) {
            ctx.strokeStyle = 'red';
            ctx.lineWidth = 2;
            ctx.strokeRect(imgObj.x, imgObj.y, imgObj.width, imgObj.height);
        }
        };
   }

  // Drop handler
  function handleDrop(event) {
    event.preventDefault();

    const raw = event.dataTransfer.getData('image');
    console.log("Raw drop data:", raw);
    if (!raw) {
      console.warn("No image data in drop event");
      return;
    }
    const payload = JSON.parse(raw);
    const srcUrl = payload.url || (payload.url && payload.url.url);
    const bbox = payload.bbox || { x: 0, y: 0, width: payload.naturalWidth || 100, height: payload.naturalHeight || 100 };

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = srcUrl;
    img.onload = () => {
      // Compute drop position relative to canvas
      const rect = canvas.getBoundingClientRect();
      const mouseX = event.clientX - rect.left;
      const mouseY = event.clientY - rect.top;
      // Determine display size: prefer the thumbnail drag size (image_width/height) if set,
      // otherwise use bbox size scaled down to a reasonable max.
      let w = image_width || bbox.width;
      let h = image_height || bbox.height;
      const maxDisplay = 300;
      if (Math.max(w, h) > maxDisplay) {
        const s = maxDisplay / Math.max(w, h);
        w = Math.round(w * s);
        h = Math.round(h * s);
      }
      //natural width and height of the image
      placedImages.push({
        url: srcUrl,
        name: payload.name,
        bbox,
        naturalWidth: payload.naturalWidth,
        naturalHeight: payload.naturalHeight,
        x: mouseX - w / 2,
        y: mouseY - h / 2,
        width: w,
        height: h
      });

      ctx.drawImage(
        img,
        bbox.x,
        bbox.y,
        bbox.width,
        bbox.height,
        mouseX - w / 2,
        mouseY - h / 2,
        w,
        h
      );
    };
    img.onerror = (err) => {
      console.error("Error loading image at drop:", srcUrl, err);
    };
  }

    function handleClick(event) {
        const rect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;
        console.log("Canvas click at:", mouseX, mouseY);

        // Find topmost image under this point
        // Iterate from end to start so that more recently placed (on top) are tested first
        for (let i = placedImages.length - 1; i >= 0; i--) {
            const obj = placedImages[i];
            console.log(`Checking image ${i} at (${obj.x}, ${obj.y}) with size (${obj.width}, ${obj.height})`);
            if (
                mouseX >= obj.x &&
                mouseX <= obj.x + obj.width &&
                mouseY >= obj.y &&
                mouseY <= obj.y + obj.height
            ) {
                ctx.strokeStyle = 'red';
                ctx.lineWidth = 2;
                ctx.strokeRect(obj.x, obj.y, obj.width, obj.height);
                return;
            }
        }
    }

  onMount(async () => {
    ctx = canvas.getContext('2d');
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const response = await fetch('/all_images');
    console.log("Response:", response);
    const data = await response.json();
    const tempCanvas = document.createElement('canvas');
    const tempCtx = tempCanvas.getContext('2d');

    const loaded = await Promise.all(
      data.images.map(async (imagePath) => {
        const url = imagePath;
        const parts = imagePath.split('/').filter(Boolean);
        const filename = parts.length ? parts[parts.length - 1] : imagePath;
        const parent = parts.length > 1 ? parts[parts.length - 2] : '';
        const name = parent ? `${parent}/${filename}` : filename;

        // load the image
        const img = new Image();
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

        // create a cropped thumbnail DataURL for compact display in the sidebar
        const maxThumb = 120; // max pixels on longest side for thumbnail
        // draw cropped region into a temporary canvas
        const cropCanvas = document.createElement('canvas');
        const cropCtx = cropCanvas.getContext('2d');
        cropCanvas.width = bbox.width;
        cropCanvas.height = bbox.height;
        // draw the image offset so the bbox region fills the crop canvas
        cropCtx.clearRect(0, 0, cropCanvas.width, cropCanvas.height);
        cropCtx.drawImage(img, -bbox.x, -bbox.y, iw, ih);

        // scale if needed
        let thumbDataUrl;
        if (Math.max(bbox.width, bbox.height) > maxThumb) {
          const scale = maxThumb / Math.max(bbox.width, bbox.height);
          const sw = Math.max(1, Math.round(bbox.width * scale));
          const sh = Math.max(1, Math.round(bbox.height * scale));
          const scaleCanvas = document.createElement('canvas');
          scaleCanvas.width = sw;
          scaleCanvas.height = sh;
          const sctx = scaleCanvas.getContext('2d');
          sctx.drawImage(cropCanvas, 0, 0, bbox.width, bbox.height, 0, 0, sw, sh);
          thumbDataUrl = scaleCanvas.toDataURL('image/png');
        } else {
          thumbDataUrl = cropCanvas.toDataURL('image/png');
        }

        return { url, name, naturalWidth: iw, naturalHeight: ih, bbox, thumb: thumbDataUrl };
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

    canvas.addEventListener('drop', handleDrop);
    canvas.addEventListener('dragover', (e) => e.preventDefault());
    canvas.addEventListener('click', handleClick);
  });

  const handleDragStart = (event, image) => {
    // include bbox and natural sizes in the drag payload
    const payload = {
      url: image.url,
      name: image.name,
      bbox: image.bbox,
      naturalWidth: image.naturalWidth,
      naturalHeight: image.naturalHeight,
    };
    event.dataTransfer.setData('image', JSON.stringify(payload));
    console.log("Drag started for image:", payload);

    // set a drag preview using the cropped thumbnail if available
    const dragImg = new Image();
    dragImg.src = image.thumb || image.url;
    // try to set drag image; browser may not show custom preview if not loaded
    try {
      event.dataTransfer.setDragImage(dragImg, 16, 16);
    } catch (e) {
      // ignore if browser prevents custom drag image
    }

    // record the thumbnail element size as a suggested placement size
    image_width = event.srcElement.clientWidth || Math.min(200, image.bbox.width);
    image_height = event.srcElement.clientHeight || Math.min(200, image.bbox.height);
  };

  const clearCanvas = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    placedImages = [];
  };

  const drawRectangle = () => {
    ctx.fillStyle = 'blue';
    ctx.fillRect(50, 50, 200, 150);
  };
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
    <button class="tool-button" on:click={clearCanvas}>Clear Canvas</button>
    <button class="tool-button" on:click={drawRectangle}>Draw Rectangle</button>
    <h3>Uploaded Images</h3>
    {#each groups as group}
      <div class="group">
        <div class="group-header" on:click={() => { openGroups[group.groupName] = !openGroups[group.groupName]; openGroups = { ...openGroups }; }}>
          <strong>{group.groupName}</strong>
          <span class="count">{group.items.length}</span>
          <span class="caret">{openGroups[group.groupName] ? '▾' : '▸'}</span>
        </div>
        {#if openGroups[group.groupName]}
          <div class="group-items">
            {#each group.items as image}
              <button
                class="image-thumbnail"
                draggable="true"
                on:dragstart={(e) => handleDragStart(e, image)}
                aria-label={`Drag ${image.name} to canvas`}
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

  <div class="canvas-container">
    <!-- portrait orientation: width x height -->
    <canvas bind:this={canvas} width="500" height="800"></canvas>
  </div>
</div>
