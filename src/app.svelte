<script>
  import Upload from './components/Upload.svelte'
  import Canvas from './components/Canvas.svelte'
</script>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barriecito&display=swap" rel="stylesheet">

<style>
  @import './app.css';
</style>

<main>
  <!-- <h1>Prosaic Editor (Upload)</h1> -->

  <h1 class="title">Promosaic </h1>
  <Upload />
  <Canvas />
</main>
