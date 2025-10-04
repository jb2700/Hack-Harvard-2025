<script>
  import { onMount } from 'svelte';

  let canvas;
  let ctx;
  let images = [];
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
    
    const { url } = JSON.parse(raw);
    console.log("Dropped image URL:", url);

    const img = new Image();
    img.src = url.url;
    img.onload = () => {
      // Compute drop position relative to canvas
      const rect = canvas.getBoundingClientRect();
      console.log("Canvas rect:", rect);
      
      const mouseX = event.clientX - rect.left;
      const mouseY = event.clientY - rect.top;

      placedImages.push({
        url,
        x: mouseX - image_width/2,
        y: mouseY - image_height/2,
        width: image_width,
        height: image_height
      });


      console.log(`Drawing image at (${mouseX}, ${mouseY}) with size (${image_width}, ${image_height})`);

      ctx.drawImage(img, mouseX - image_width/2, mouseY - image_height/2, image_width, image_height);
    };
    img.onerror = (err) => {
      console.error("Error loading image at drop:", url, err);
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

    const response = await fetch('http://localhost:5054/all_images');
    console.log("Response:", response);
    const data = await response.json();
    // images = data.images;
    images = data.images.map(image => ({
        url: `http://localhost:5054${image}`,
        name: image
    }));
    
    console.log("Fetched images:", images);

    canvas.addEventListener('drop', handleDrop);
    canvas.addEventListener('dragover', (e) => e.preventDefault());
    canvas.addEventListener('click', handleClick);
  });

  const handleDragStart = (event, url) => {
    // Set the serialized data for drop logic
    event.dataTransfer.setData('image', JSON.stringify({ url }));
    console.log("Drag started for image:", url);

    // Create an image element to serve as the drag preview
    const dragImg = new Image();
    dragImg.src = url;
    console.log("event start:", event);
    image_width = event.srcElement.clientWidth;
    image_height = event.srcElement.clientHeight;
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
    width: 200px;
    background-color: #f4f4f4;
    padding: 10px;
    border-right: 1px solid #ddd;
  }

  .canvas-container {
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
    {#each images as image}
      <button
        class="image-thumbnail"
        draggable="true"
        on:dragstart={(e) => handleDragStart(e, image)}
        aria-label={`Drag ${image} to canvas`}
      >
        <img src={image.url} alt={image.name} />
        <p>{image.name}</p> 
      </button>
    {/each}
  </div>

  <div class="canvas-container">
    <canvas bind:this={canvas} width="800" height="600"></canvas>
  </div>
</div>
