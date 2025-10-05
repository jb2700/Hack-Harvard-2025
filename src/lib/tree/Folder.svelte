<script>
  import { createEventDispatcher } from 'svelte';
  import Folder from './Folder.svelte'; // recursion

  export let node;
  export let path = '';

  const dispatch = createEventDispatcher();
  let isOpen = false;
  let compositeCache = null; // cached dataUrl for this folder's composite preview

  function toggle() {
    isOpen = !isOpen;
  }

  function onFileClick(item) {
    dispatch('open', { item });
  }

  function onFileDragStart(e, item) {
    dispatch('drag', { event: e, item });
  }

  async function buildComposite() {
    if (compositeCache) return compositeCache;
    try {
      // compute bounding box of all items to know composite size
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const f of node.files) {
        const b = f.bbox || { x:0,y:0,width:f.naturalWidth||1, height:f.naturalHeight||1 };
        minX = Math.min(minX, b.x);
        minY = Math.min(minY, b.y);
        maxX = Math.max(maxX, b.x + b.width);
        maxY = Math.max(maxY, b.y + b.height);
      }
      if (!isFinite(minX)) {
        minX = 0; minY = 0; maxX = 64; maxY = 64;
      }
      const cw = Math.max(1, Math.ceil(maxX - minX));
      const ch = Math.max(1, Math.ceil(maxY - minY));

      const maxSide = 200;
      const scale = Math.min(1, maxSide / Math.max(cw, ch));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(cw * scale));
      canvas.height = Math.max(1, Math.round(ch * scale));
      const ctx = canvas.getContext('2d');

      for (const f of node.files) {
        try {
          const img = new Image();
          img.crossOrigin = 'anonymous';
          img.src = f.thumb || f.url;
          await new Promise((res, rej) => { img.onload = res; img.onerror = rej; });
          const b = f.bbox || { x:0,y:0,width:img.naturalWidth, height:img.naturalHeight };
          const dx = (b.x - minX) * scale;
          const dy = (b.y - minY) * scale;
          const dw = Math.max(1, Math.round(b.width * scale));
          const dh = Math.max(1, Math.round(b.height * scale));
          ctx.drawImage(img, 0, 0, img.naturalWidth || dw, img.naturalHeight || dh, dx, dy, dw, dh);
        } catch (inner) {
          // ignore individual failures
        }
      }

      compositeCache = canvas.toDataURL('image/png');
      return compositeCache;
    } catch (err) {
      console.warn('buildComposite failed', err);
      return null;
    }
  }

  // create drag payload and set drag image
  async function onFolderDragStart(e) {
    try {
      const composite = await buildComposite();
      // compute folder bbox and scale (recompute minimal values to pass in payload)
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const f of node.files) {
        const b = f.bbox || { x:0,y:0,width:f.naturalWidth||1, height:f.naturalHeight||1 };
        minX = Math.min(minX, b.x);
        minY = Math.min(minY, b.y);
        maxX = Math.max(maxX, b.x + b.width);
        maxY = Math.max(maxY, b.y + b.height);
      }
      if (!isFinite(minX)) { minX = 0; minY = 0; maxX = 64; maxY = 64; }
      const cw = Math.max(1, Math.ceil(maxX - minX));
      const ch = Math.max(1, Math.ceil(maxY - minY));
      const maxSide = 200;
      const scale = Math.min(1, maxSide / Math.max(cw, ch));

      const payload = { type: 'folder', name: node.name, composite: composite, items: node.files, bbox: { x: minX, y: minY, width: cw, height: ch }, scale };
      // dispatch event for parent handlers
      dispatch('drag', { event: e, item: payload });

      try {
        e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'folder', name: node.name }));
        if (composite) e.dataTransfer.setData('application/folder-composite', composite);
      } catch (err) { /* ignore */ }

      try {
        if (composite) {
          const img = new Image();
          img.src = composite;
          e.dataTransfer.setDragImage(img, img.width/2 || 20, img.height/2 || 20);
        }
      } catch (err) { /* ignore */ }
    } catch (err) {
      console.warn('Folder drag composite failed', err);
    }
  }
</script>

<style>
  .folder {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    padding: 4px 6px;
    border-radius: 4px;
    background: transparent;
    width: 100%;
    text-align: left;
  }
  .folder:hover { background: rgba(0,0,0,0.03); }

  /* Container that holds nested folders and the file-entries wrapper. Keep
     scrolling behavior on this container when there are many items. */
  .files {
    margin-left: 16px;
  }

  /* Explicit flex wrapper for file entries so thumbnails wrap reliably.
     Avoids the experimental :has() selector and keeps styles local. */
  .file-entries {
    display: flex;
    align-content: flex-start;
    flex-wrap: wrap;
    flex-direction: row;
    gap: 8px;
  }
  .file-entry {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 6px;
    border-radius: 4px;
    background: var(--gb-panel);
  }
  .file-entry:hover { background: rgba(0,0,0,0.02); }
  .thumb { width: 48px; height: auto; border: 1px solid #ddd; }
  .composite-thumb { width: 56px; height: 56px; object-fit: contain; border: 1px solid #ddd; margin-left: auto; }
</style>

<div>
  <button class="folder" type="button" on:click={toggle} on:dragstart={(e) => onFolderDragStart(e)} draggable={true} role="treeitem" aria-expanded={isOpen} aria-selected={isOpen} tabindex="0">
    <span>{isOpen ? '\u25be' : '\u25b8'}</span>
    <strong>{node.name}</strong>
    {#if node.files && node.files.length}
      <span style="opacity:0.6;margin-left:6px">{node.files.length}</span>
    {/if}
    {#if node.files && node.files.length}
      {#await buildComposite()}
        <img class="composite-thumb" src="" alt="" aria-hidden="true" style="visibility:hidden" />
      {:then dataUrl}
        {#if dataUrl}
          <img class="composite-thumb" src={dataUrl} alt={`Preview of ${node.name}`} />
        {:else}
          <div class="composite-thumb" aria-hidden="true" style="display:inline-block"></div>
        {/if}
      {:catch _}
        <div class="composite-thumb" aria-hidden="true" style="display:inline-block"></div>
      {/await}
    {/if}
  </button>

  {#if isOpen}
    <div class="files" role="list">
      {#each node.children as child}
        <Folder node={child} path={path + '/' + child.name} on:open={(e) => dispatch('open', e.detail)} on:drag={(e) => dispatch('drag', e.detail)} />
      {/each}

      <div class="file-entries">
      {#each node.files as file}
        <button class="file-entry" type="button" draggable="true" on:dragstart={(e) => onFileDragStart(e, file)} on:click={() => onFileClick(file)}>
          <img src={file.thumb} alt={file.name} class="thumb" />
        </button>
      {/each}
      </div>
    </div>
  {/if}
</div>
