const CACHE_NAME = "aurals-lc-v9";
const BASE_PATH = "./";

// Install event - just skip waiting
self.addEventListener("install", (event) => {
	event.waitUntil(self.skipWaiting());
});

// Activate event - clean up old caches
self.addEventListener("activate", (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((cacheNames) => {
				return Promise.all(
					cacheNames.map((cacheName) => {
						return caches.delete(cacheName);
					})
				);
			})
			.then(() => self.clients.claim())
	);
});

// Fetch event - always fetch from network
self.addEventListener("fetch", (event) => {
	// Only handle requests from our origin
	if (!event.request.url.startsWith(self.location.origin)) {
		return; // Let browser handle external requests normally
	}

	event.respondWith(
		fetch(event.request).catch(() => {
			// If network fails, return a basic offline response
			if (event.request.url.indexOf(".json") > -1) {
				return new Response(
					JSON.stringify({ error: "Data unavailable offline" }),
					{
						headers: { "Content-Type": "application/json" },
					}
				);
			}
			// For HTML requests, return a basic offline page
			if (event.request.mode === "navigate") {
				return new Response(
					"<html><body><h1>Offline</h1><p>Please check your internet connection and try again.</p></body></html>",
					{
						headers: { "Content-Type": "text/html" },
					}
				);
			}
		})
	);
});
