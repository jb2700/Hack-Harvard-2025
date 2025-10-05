<script>
  import Canvas from './components/Canvas.svelte'
</script>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barriecito&display=swap" rel="stylesheet">

<style>
:global(:root) {
  --gb-bg: #1d2021; /* dark background */
  --gb-panel: #3c3836; /* sidebar */
  --gb-panel-variant: #32302f; /* toolbar / lighter panel */
  --gb-text: #fbf1c7; /* main text */
  --gb-muted: #bdae93; /* muted text */
  --gb-border: #7c6f64; /* outlines */
  --gb-accent: #fe8019; /* orange */
  --gb-button: #504945; /* button bg */
  --gb-button-hover: #665c54;
  --gb-canvas-edge: #2a2a28;
}
.title {
  font-family: "Barriecito";
  font-size: 5rem;
  font-weight: bold;
  text-align: center;
  margin: 0rem 0;
  color: #333;
}
:global(html, body) {
  height: 100%;
  margin: 0;
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
  background-color: var(--gb-bg);
}
main {
  padding: 2rem;
}

</style>

<main>
  <!-- <h1>Prosaic Editor (Upload)</h1> -->

  <h1 class="title">Promosaic </h1>
  <Canvas />
</main>
