import { writable } from 'svelte/store'
// simple integer counter — bumping it signals listeners to refetch
export const imagesRefresh = writable(0)
