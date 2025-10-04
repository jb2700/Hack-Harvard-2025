<script>
  import Folder from './Folder.svelte'; // allow recursion
  import { createEventDispatcher } from 'svelte';

  export let node;
  export let path = '';

  const dispatch = createEventDispatcher();
  let isOpen = false;

  function toggle() {
    isOpen = !isOpen;
  }

  function onFileClick(item) {
    dispatch('open', { item });
  }

  function onFileDragStart(e, item) {
    dispatch('drag', { event: e, item });
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
  .files { margin-left: 16px; }
  .file-entry {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 6px;
    border-radius: 4px;
  }
  .file-entry:hover { background: rgba(0,0,0,0.02); }
  .thumb { width: 48px; height: auto; border: 1px solid #ddd; }
  .file-entry .filename { font-size: 12px; }
</style>

<div>
  <button class="folder" type="button" on:click={toggle} role="treeitem" aria-expanded={isOpen} aria-selected={isOpen} tabindex="0">
    <span>{isOpen ? '▾' : '▸'}</span>
    <strong>{node.name}</strong>
    {#if node.files && node.files.length}
      <span style="opacity:0.6;margin-left:6px">{node.files.length}</span>
    {/if}
  </button>

  {#if isOpen}
    <div class="files" role="list">
      {#each node.children as child}
        <Folder node={child} path={path + '/' + child.name} on:open={(e) => dispatch('open', e.detail)} on:drag={(e) => dispatch('drag', e.detail)} />
      {/each}

      {#each node.files as file}
  <button class="file-entry" type="button" draggable="true" on:dragstart={(e) => onFileDragStart(e, file)} on:click={() => onFileClick(file)}>
          <img src={file.thumb} alt={file.name} class="thumb" />
        </button>
      {/each}
    </div>
  {/if}
</div>
