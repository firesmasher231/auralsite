const CACHE_NAME = "aurals-lc-v7";
const BASE_PATH = "./";
const ASSETS_TO_CACHE = [
	`${BASE_PATH}`,
	`${BASE_PATH}index.html`,
	`${BASE_PATH}manifest.json`,
	`${BASE_PATH}icons/headphones_192_192.png`,
	`${BASE_PATH}icons/headphones_512_512.png`,
	`${BASE_PATH}icons/volume-icon.svg`,
	`${BASE_PATH}icons/muted.svg`,
];

// In notification options (future use)
const options = {
	body: "New content available",
	icon: `${BASE_PATH}icons/headphones_192_192.png`,
	badge: `${BASE_PATH}icons/headphones_192_192.png`,
};

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
	// Only handle requests from our origin
	if (!event.request.url.startsWith(self.location.origin)) {
		return; // Let browser handle external requests normally
	}

	// For navigation requests (HTML pages)
	if (event.request.mode === "navigate") {
		event.respondWith(
			fetch(event.request).catch(() => {
				return caches.match(`${BASE_PATH}index.html`);
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
