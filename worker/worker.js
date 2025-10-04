export default {
  async fetch(request, env) {
    try {
      const reqJson = await request.json();
      const { image: imgB64, mask: maskB64, prompt } = reqJson;

      // Decode base64 → bytes
      const imageBytes = Uint8Array.from(atob(imgB64), c => c.charCodeAt(0));
      const maskBytes = Uint8Array.from(atob(maskB64), c => c.charCodeAt(0));

      // Call the Workers AI inpainting model
      const aiResponse = await env.AI.run("@cf/runwayml/stable-diffusion-v1-5-inpainting", {
        prompt,
        image: { body: imageBytes, contentType: "image/png" },
        mask: { body: maskBytes, contentType: "image/png" },
        num_steps: 20
      });

      // aiResponse.image is the result image (PNG or JPEG)
      const arrBuf = await aiResponse.image.arrayBuffer();
      const outBytes = new Uint8Array(arrBuf);
      // Encode back to base64
      const outB64 = btoa(String.fromCharCode(...outBytes));

      return new Response(JSON.stringify({ output_image: outB64 }), {
        headers: { "Content-Type": "application/json" }
      });

    } catch (err) {
      return new Response("Error: " + err.toString(), { status: 500 });
    }
  }
};
