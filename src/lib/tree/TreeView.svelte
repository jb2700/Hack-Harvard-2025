<script>
  import Folder from './Folder.svelte';
  import { createEventDispatcher } from 'svelte';

  export let items = [];
  const dispatch = createEventDispatcher();

  function buildTree(items) {
    // root map of folderName -> { __children: Map, __files: [] }
    const root = new Map();
    // helper root entry to hold files at root level
    const rootEntry = { __children: root, __files: [] };

    for (const it of items) {
      const parts = it.name.split('/').filter(Boolean);
      // current map and entry start at root
      let nodeMap = root;
      let currentEntry = rootEntry;

      // iterate only up to parent folder (exclude the last segment which is the filename)
      for (let i = 0; i < Math.max(0, parts.length - 1); i++) {
        const part = parts[i];
        if (!nodeMap.has(part)) nodeMap.set(part, { __children: new Map(), __files: [] });
        currentEntry = nodeMap.get(part);
        nodeMap = currentEntry.__children;
      }

      // push the file item into the parent folder's __files
      currentEntry.__files.push(it);
    }

    function toArray(map) {
      const out = [];
      for (const [name, val] of map.entries()) {
        out.push({ name, children: toArray(val.__children), files: val.__files });
      }
      return out;
    }

    return toArray(root);
  }

  $: tree = buildTree(items || []);
</script>

<style>
  .tree { padding: 6px; font-family: system-ui; font-size: 13px; }
</style>

<div class="tree" role="tree">
  {#each tree as node}
    <Folder node={node} path={node.name} on:open={(e) => dispatch('open', e.detail)} on:drag={(e) => dispatch('drag', e.detail)} />
  {/each}
</div>
