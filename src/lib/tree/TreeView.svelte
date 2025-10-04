<script>
  import Folder from './Folder.svelte';
  import { createEventDispatcher } from 'svelte';

  export let items = [];
  const dispatch = createEventDispatcher();

  function buildTree(items) {
    const root = new Map();
    for (const it of items) {
      const parts = it.name.split('/').filter(Boolean);
      let node = root;
      for (let i = 0; i < parts.length; i++) {
        const part = parts[i];
        const isFile = i === parts.length - 1;
        if (!node.has(part)) node.set(part, { __children: new Map(), __files: [] });
        const entry = node.get(part);
        if (isFile) entry.__files.push(it);
        node = entry.__children;
      }
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
