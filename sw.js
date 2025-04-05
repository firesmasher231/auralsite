const CACHE_NAME = "aurals-lc-v1";
const ASSETS_TO_CACHE = [
	"/",
	"/index.html",
	"/manifest.json",
	"/icons/headphones.svg",
	"/icons/volume-icon.svg",
	"/icons/muted.svg",
	"https://cdn.tailwindcss.com",
	"https://fonts.googleapis.com/css2?family=VT323&display=swap",
];

// Install event - cache core app files
self.addEventListener("install", (event) => {
	event.waitUntil(
		caches
			.open(CACHE_NAME)
			.then((cache) => {
				console.log("Opened cache");
				return cache.addAll(ASSETS_TO_CACHE);
			})
			.then(() => self.skipWaiting())
	);
});

// Activate event - clean up old caches
self.addEventListener("activate", (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((cacheNames) => {
				return Promise.all(
					cacheNames.map((cacheName) => {
						if (cacheName !== CACHE_NAME) {
							return caches.delete(cacheName);
						}
					})
				);
			})
			.then(() => self.clients.claim())
	);
});

// Fetch event - serve from cache if available, otherwise fetch from network
self.addEventListener("fetch", (event) => {
	// Skip cross-origin requests
	if (
		!event.request.url.startsWith(self.location.origin) &&
		!event.request.url.includes("cdn.tailwindcss.com") &&
		!event.request.url.includes("fonts.googleapis.com")
	) {
		return;
	}

	// For navigation requests (HTML pages)
	if (event.request.mode === "navigate") {
		event.respondWith(
			fetch(event.request).catch(() => {
				return caches.match("/index.html");
			})
		);
		return;
	}

	// For other requests - cache-first strategy
	event.respondWith(
		caches.match(event.request).then((cachedResponse) => {
			if (cachedResponse) {
				return cachedResponse;
			}

			return fetch(event.request)
				.then((response) => {
					// Don't cache if not a valid response
					if (
						!response ||
						response.status !== 200 ||
						response.type !== "basic"
					) {
						return response;
					}

					// Cache successful responses
					const responseToCache = response.clone();
					caches.open(CACHE_NAME).then((cache) => {
						cache.put(event.request, responseToCache);
					});

					return response;
				})
				.catch(() => {
					// If both cache and network fail, try to return a fallback
					if (event.request.url.indexOf(".json") > -1) {
						return new Response(
							JSON.stringify({ error: "Data unavailable offline" }),
							{
								headers: { "Content-Type": "application/json" },
							}
						);
					}
				});
		})
	);
});

// Handle JSON fetch separately to cache timestamp and language data
self.addEventListener("fetch", (event) => {
	if (
		event.request.url.includes("timestamps/") ||
		event.request.url.includes("languages.json")
	) {
		event.respondWith(
			caches.open("aurals-data-cache").then((cache) => {
				return cache
					.match(event.request)
					.then((cachedResponse) => {
						const fetchPromise = fetch(event.request).then(
							(networkResponse) => {
								cache.put(event.request, networkResponse.clone());
								return networkResponse;
							}
						);

						return cachedResponse || fetchPromise;
					})
					.catch(() => {
						// Return empty JSON if offline and not cached
						return new Response(JSON.stringify({}), {
							headers: { "Content-Type": "application/json" },
						});
					});
			})
		);
	}
});
