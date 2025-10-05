<script>
  import { onMount } from 'svelte'
  import { uploadedImage } from '../stores/uploaded.js'
  import { imagesRefresh } from '../stores/imagesRefresh.js'
  let file = null
  let previewUrl = null
  let status = ''

  function onFileChange(e) {
    const f = e.target.files[0]
    if (!f) return
    file = f
    previewUrl = URL.createObjectURL(f)
  }

  async function upload() {
    if (!file) return
    status = 'Uploading and generating masks...'
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await fetch('/upload', { method: 'POST', body: form })
      const json = await res.json()
      if (res.ok) {
        uploadedImage.set(json.url)
        // trigger a refresh so the image list updates
        imagesRefresh.update(n => n + 1)
        status = 'Uploaded'
      } else {
        status = 'Error: ' + (json.error || res.statusText)
      }
    } catch (err) {
      status = 'Upload failed: ' + err.message
    }
  }
</script>

<div class="upload">
  <input type="file" accept="image/*" on:change={onFileChange} />
  {#if previewUrl}
    <div style="margin-top:8px">
      <img src={previewUrl} alt="preview" style="max-width:300px; max-height:200px" />
    </div>
    <button on:click={upload} style="margin-top:8px">Upload</button>
  {/if}
  {#if status}
    <div style="margin-top:8px">{status}</div>
  {/if}
</div>
