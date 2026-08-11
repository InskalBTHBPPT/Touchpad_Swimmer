(function ($) {
	("use strict");

	$(document).ready(function () {
		initYouTubeGallery();
	});

	function initYouTubeGallery() {
		// Helper for parsing JSON data
		function parseMaybeJSON(val, fallback) {
			if (typeof val === "string") {
				try {
					return JSON.parse(val);
				} catch (e) {
					return fallback;
				}
			}
			return typeof val === "object" && val !== null ? val : fallback;
		}

		// Helper to truncate text responsively
		function truncateText(text, length) {
			if (!text) return "";
			const width = $(window).width();
			let maxLength;
			if (width < 600) {
				maxLength = length.sm || length.lg;
			} else if (width < 900) {
				maxLength = length.md || length.lg;
			} else {
				maxLength = length.lg;
			}
			return text.length > maxLength
				? text.substring(0, maxLength) + "..."
				: text;
		}

		// Helper to sort videos
		function sortVideos(videos, sortBy) {
			const sorted = [...videos];
			switch (sortBy) {
				case "title":
					return sorted.sort((a, b) =>
						a.title.localeCompare(b.title, undefined, {
							sensitivity: "base",
						})
					);
				case "latest":
					return sorted.sort(
						(a, b) =>
							new Date(b.publishedAt).getTime() -
							new Date(a.publishedAt).getTime()
					);
				case "date":
					return sorted.sort(
						(a, b) =>
							new Date(a.publishedAt).getTime() -
							new Date(b.publishedAt).getTime()
					);
				case "popular":
					return sorted.sort((a, b) => (b.viewCount || 0) - (a.viewCount || 0));
				default:
					return videos;
			}
		}

		// Extract playlist ID from URL or direct ID, and handle channel URLs/handles
		function getPlaylistId(input) {
			if (!input) return "";
			try {
				const url = new URL(input);
				if (url.hostname === "www.youtube.com") {
					if (url.pathname.startsWith("/channel/")) {
						return url.pathname.split("/channel/")[1];
					} else if (url.pathname.startsWith("/@")) {
						return url.pathname.substring(2); // Return handle for later resolution
					} else if (url.searchParams.get("list")) {
						return url.searchParams.get("list");
					}
				}
				return input;
			} catch (e) {
				return input;
			}
		}

		// Resolve handle to channel ID using YouTube API
		function resolveHandleToChannelId(handle, apiKey, callback) {
			$.get(
				`https://www.googleapis.com/youtube/v3/search?part=snippet&q=${encodeURIComponent(
					handle
				)}&type=channel&key=${apiKey}`
			)
				.done(function (data) {
					if (data.items && data.items.length > 0) {
						callback(data.items[0].snippet.channelId);
					} else {
						callback(null);
					}
				})
				.fail(function () {
					callback(null);
				});
		}

		// Helper function to generate video player iframe
		function generatePlayerIframe(videoId, config) {
			const params = [
				`autoplay=${config.autoplay ? "1" : "0"}`,
				`loop=${config.loop ? "1" : "0"}`,
				`mute=${config.mute ? "1" : "0"}`,
				`controls=${config.showPlayerControl ? "1" : "0"}`,
				`modestbranding=${config.hideYoutubeLogo ? "1" : "0"}`,
				config.loop ? `playlist=${videoId}` : null,
			]
				.filter(Boolean)
				.join("&");

			return `
				<div class="ultp-ytg-video-wrapper">
					<iframe 
						src="https://www.youtube.com/embed/${videoId}?${params}"
						title="YouTube Video"
						frameborder="0"
						allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
						allowfullscreen
					></iframe>
				</div>
			`;
		}

		// Generate text content (title and description)
		function getYoutubeTextContent(
			enableTitle,
			title,
			titleLength,
			enableDesc,
			description,
			descriptionLength,
			videoId
		) {
			let html = '<div class="ultp-ytg-content">';
			if (enableTitle) {
				html += `<div class="ultp-ytg-title"><a href="https://www.youtube.com/watch?v=${videoId}" target="_blank" rel="noopener noreferrer">${truncateText(
					title,
					titleLength
				)}</a></div>`;
			}
			if (enableDesc) {
				html += `<div class="ultp-ytg-description">${truncateText(
					description,
					descriptionLength
				)}</div>`;
			}
			html += "</div>";
			return html;
		}

		// Initialize YouTube Gallery
		$(".wp-block-ultimate-post-youtube-gallery").each(function () {
			const $block = $(this);
			const $wrapper = $block.find(".ultp-block-wrapper");
			let $container = $block.find(".ultp-ytg-view-grid, .ultp-ytg-container");
			const $loadMoreBtn = $block.find(".ultp-ytg-loadmore-btn");

			// Get configuration from data attributes
			const config = {
				playlistIdOrUrl: $block.data("playlist") || "",
				apiKey: $block.data("api-key") || "",
				cacheDuration: parseInt($block.data("cache-duration")) || 0,
				sortBy: $block.data("sort-by") || "date",
				galleryLayout: $block.data("gallery-layout") || "grid",
				videosPerPage: parseMaybeJSON($block.data("videos-per-page"), {
					lg: 9,
					md: 6,
					sm: 3,
				}),
				showVideoTitle: $block.data("show-video-title") == "1",
				videoTitleLength: parseMaybeJSON($block.data("video-title-length"), {
					lg: 50,
					md: 50,
					sm: 50,
				}),
				loadMoreEnable: $block.data("load-more-enable") == "1",
				moreButtonLabel: $block.data("more-button-label") || "More Videos",
				autoplay: $block.data("autoplay") == "1",
				loop: $block.data("loop") == "1",
				mute: $block.data("mute") == "1",
				showPlayerControl: $block.data("show-player-control") == "1",
				hideYoutubeLogo: $block.data("hide-youtube-logo") == "1",
				showDescription: $block.data("show-description") == "1",
				videoDescriptionLength: parseMaybeJSON(
					$block.data("video-description-length"),
					{
						lg: 100,
						md: 100,
						sm: 100,
					}
				),
				imageHeightRatio: $block.data("image-height-ratio") || "16-9",
				galleryColumn: parseMaybeJSON($block.data("gallery-column"), {
					lg: 3,
					md: 2,
					sm: 1,
				}),
				displayType: $block.data("display-type") || "grid",
				enableListView: $block.data("enable-list-view") == "1",
				enableIconAnimation: $block.data("enable-icon-animation") == "1",
				defaultYoutubeIcon: $block.data("enable-youtube-icon") == "1",
				imgHeight: $block.data("img-height"),
			};

			let playlistId = getPlaylistId(config.playlistIdOrUrl);

			// If it's a handle (starts with @), resolve to channel ID
			if (playlistId.startsWith("@")) {
				const handle = playlistId.substring(1);
				resolveHandleToChannelId(handle, config.apiKey, function (channelId) {
					if (channelId) {
						playlistId = channelId;
						proceedWithPlaylist(playlistId);
					} else {
						$wrapper.html(
							'<p style="color:#888">Invalid handle or API key.</p>'
						);
					}
				});
			} else {
				proceedWithPlaylist(playlistId);
			}

			function proceedWithPlaylist(playlistId) {
				// Convert channel ID to uploads playlist ID
				if (playlistId.startsWith("UC")) {
					playlistId = "UU" + playlistId.substring(2);
				}

				if (!playlistId || !config.apiKey) {
					$wrapper.html(
						'<p style="color:#888">Please provide both YouTube playlist ID/URL and API key.</p>'
					);
					return;
				}

				// State management
				let allVideos = [];
				let shownCount = config.videosPerPage.lg || 9;
				let activeVideo = null;
				let playingId = null;

				// Update responsive counts
				function updateResponsiveCounts() {
					const width = $(window).width();
					if (width < 600) {
						shownCount = Math.max(shownCount, config.videosPerPage.sm || 3);
					} else if (width < 900) {
						shownCount = Math.max(shownCount, config.videosPerPage.md || 6);
					} else {
						shownCount = Math.max(shownCount, config.videosPerPage.lg || 9);
					}
				}

				// Render videos for playlist layout
				function renderPlaylistLayout(videos) {
					if (!videos.length) {
						$container.html("<p>No videos found in this playlist.</p>");
						return;
					}

					if (!activeVideo) {
						activeVideo = videos[0];
					}

					let html = '<div class="ultp-ytg-main">';
					// Generate player iframe and place .ultp-ytg-content inside .ultp-ytg-video-wrapper
					const playerWrapper = `
						<div class="ultp-ytg-video-wrapper">
							<iframe 
								src="https://www.youtube.com/embed/${activeVideo.videoId}?${[
						`autoplay=${config.autoplay ? "1" : "0"}`,
						`loop=${config.loop ? "1" : "0"}`,
						`mute=${config.mute ? "1" : "0"}`,
						`controls=${config.showPlayerControl ? "1" : "0"}`,
						`modestbranding=${config.hideYoutubeLogo ? "1" : "0"}`,
						config.loop ? `playlist=${activeVideo.videoId}` : null,
					]
						.filter(Boolean)
						.join("&")}"
								title="YouTube Video"
								frameborder="0"
								allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
								allowfullscreen
							></iframe>
							${getYoutubeTextContent(
								config.showVideoTitle,
								activeVideo.title,
								config.videoTitleLength,
								config.showDescription,
								activeVideo.description,
								config.videoDescriptionLength,
								activeVideo.videoId
							)}
						</div>
					`;
					html += playerWrapper;
					html += "</div>";

					html += '<div class="ultp-ytg-playlist-sidebar">';
					html += '<div class="ultp-ytg-playlist-items">';
					videos.forEach(function (video) {
						const isActive = video.videoId === activeVideo.videoId;
						html += `
							<div class="ultp-ytg-playlist-item ${
								isActive ? "active" : ""
							}" data-video-id="${video.videoId}">
								<img src="${video.thumbnail}" alt="${video.title}" loading="lazy" />
								<div class="ultp-ytg-playlist-item-content">
									<div class="ultp-ytg-playlist-item-title">
										${truncateText(video.title, config.videoTitleLength)}
									</div>
								</div>
							</div>
						`;
					});
					html += "</div></div>";

					$container.html(html);
				}

				// Render videos for grid/list layout
				function renderGridLayout(videos, count) {
					if (!videos.length) {
						$container.html("<p>No videos found in this playlist.</p>");
						return;
					}

					const displayedVideos = videos.slice(0, count);
					let html = "";
					displayedVideos.forEach(function (video) {
						const isPlaying = playingId === video.videoId;
						html += `<div class="ultp-ytg-item${isPlaying ? " active" : ""}">`;
						html += `<div class="ultp-ytg-video">`;

						if (isPlaying) {
							html += generatePlayerIframe(video.videoId, config);
						} else {
							// enableIconAnimation
							const getSvgIcon = $(".ultp-ytg-play__icon").html();
							html += `
								<img src="${video.thumbnail}" alt="${
								video.title
							}" loading="lazy" data-video-id="${
								video.videoId
							}" style="cursor:pointer;" />
								<div class="ultp-ytg-play__icon${
									config.enableIconAnimation ? " ytg-icon-animation" : ""
								}">
									${getSvgIcon}
								</div>
							`;
						}

						html += `</div>`;
						html += `<div class="ultp-ytg-inside">`;
						html += getYoutubeTextContent(
							config.showVideoTitle,
							video.title,
							config.videoTitleLength,
							config.showDescription,
							video.description,
							config.videoDescriptionLength,
							video.videoId
						);
						html += `</div></div>`;
					});

					$container.html(html);

					// Update load more button visibility
					if (config.loadMoreEnable && count < videos.length) {
						$loadMoreBtn.show();
					} else {
						$loadMoreBtn.hide();
					}
				}

				// Render based on layout type
				function renderVideos(videos, count) {
					if (config.galleryLayout === "playlist") {
						renderPlaylistLayout(videos);
					} else {
						renderGridLayout(videos, count);
					}
				}

				// Fetch videos from YouTube API
				const cacheKey = `ultp_youtube_gallery_${playlistId}_${config.apiKey}_${config.sortBy}_${config.imgHeight}`;
				const duration = config.cacheDuration;
				let cached = null;

				try {
					cached = JSON.parse(localStorage.getItem(cacheKey));
				} catch (e) {
					cached = null;
				}

				const now = Date.now();
				if (
					cached &&
					cached.data &&
					cached.timestamp &&
					duration > 0 &&
					now - cached.timestamp < duration * 1000
				) {
					allVideos = sortVideos(cached.data, config.sortBy);
					renderVideos(allVideos, shownCount);
				} else {
					// Only show loading skeleton for grid/list layouts, not for playlist layout
					if (config.galleryLayout !== "playlist") {
						$container.html(`
							<div class="ultp-ytg-loading gallery-postx gallery-active">
								<div class="skeleton-box"></div>
								<div class="skeleton-box"></div>
								<div class="skeleton-box"></div>
								<div class="skeleton-box"></div>
								<div class="skeleton-box"></div>
								<div class="skeleton-box"></div>
							</div>
						`);
					} else {
						$container.html(`
							<div class="ultp-ytg-loading ultp-ytg-playlist-loading">
								<div class="ytg-loader"></div>
							</div>`);
					}

					$.get("https://www.googleapis.com/youtube/v3/playlistItems", {
						part: "snippet",
						maxResults: 50,
						playlistId: playlistId,
						key: config.apiKey,
					})
						.done(function (data) {
							setTimeout(function () {
								$container.empty(); // Remove loading after 3s
								if (data.error) {
									$container.html(
										`<div class="ultp-ytg-error">${
											data.error.message || "Failed to fetch playlist."
										}</div>`
									);
									return;
								}

								const videos = (data.items || [])
									.filter(function (item) {
										return (
											item.snippet.title !== "Private video" &&
											item.snippet.title !== "Deleted video"
										);
									})
									.map(function (item) {
										return {
											videoId: item.snippet.resourceId.videoId,
											title: item.snippet.title,
											thumbnail:
												(item.snippet.thumbnails &&
													item.snippet.thumbnails[config.imgHeight] &&
													item.snippet.thumbnails[config.imgHeight].url) ||
												item.snippet.thumbnails[config.imgHeight].url ||
												item.snippet.thumbnails?.medium?.url ||
												"",
											publishedAt: item.snippet.publishedAt || "",
											description: item.snippet.description || "",
											viewCount: 0, // Initialize for popular sorting
										};
									}); // If sorting by popular, fetch view counts
								if (config.sortBy === "popular") {
									const videoIds = videos.map((v) => v.videoId).join(",");
									$.get(
										`https://www.googleapis.com/youtube/v3/videos?part=statistics&id=${videoIds}&key=${config.apiKey}`
									)
										.done(function (statsData) {
											if (statsData.items) {
												const statsMap = {};
												statsData.items.forEach(function (item) {
													statsMap[item.id] = item.statistics.viewCount;
												});
												videos.forEach(function (v) {
													v.viewCount = parseInt(statsMap[v.videoId] || 0);
												});
											}
											allVideos = sortVideos(videos, config.sortBy);
											if (duration > 0) {
												try {
													localStorage.setItem(
														cacheKey,
														JSON.stringify({
															data: videos,
															timestamp: now,
														})
													);
												} catch (e) {
													console.warn("Failed to cache videos:", e);
												}
											}
											renderVideos(allVideos, shownCount);
										})
										.fail(function () {
											console.warn(
												"Failed to fetch video statistics for popular sorting."
											);
											allVideos = sortVideos(videos, config.sortBy);
											renderVideos(allVideos, shownCount);
										});
								} else {
									allVideos = sortVideos(videos, config.sortBy);
									if (duration > 0) {
										try {
											localStorage.setItem(
												cacheKey,
												JSON.stringify({
													data: videos,
													timestamp: now,
												})
											);
										} catch (e) {
											console.warn("Failed to cache videos:", e);
										}
									}
									renderVideos(allVideos, shownCount);
								}
							}, 2000);
						})
						.fail(function () {
							setTimeout(function () {
								$container.empty();
								$container.html(
									'<div class="ultp-ytg-error">Failed to fetch videos. Please try again.</div>'
								);
							}, 3000);
						});
				}

				// Event handlers
				$block.on("click", ".ultp-ytg-playlist-item", function () {
					const videoId = $(this).data("video-id");
					if (!videoId) return;

					activeVideo = allVideos.find(function (v) {
						return v.videoId === videoId;
					});

					if (activeVideo) {
						renderPlaylistLayout(allVideos);
					}
				});
				// Make clicking the play icon also start the video with loader fallback (per item)
				$block.on("click", ".ultp-ytg-play__icon", function () {
					// Find the previous img[data-video-id] sibling to get the videoId
					const $img = $(this).siblings("img[data-video-id]");
					const videoId = $img.data("video-id");
					if (!videoId) return;
					// Find the closest .ultp-ytg-item and its .ultp-ytg-video
					const $item = $(this).closest(".ultp-ytg-item");
					const $videoDiv = $item.find(".ultp-ytg-video");
					// Show loader only in this video area
					$videoDiv.html(
						'<div class="ultp-ytg-loading"><div class="ytg-loader"></div></div>'
					);
					// Add active class to this item, remove from others
					$item
						.addClass("active")
						.siblings(".ultp-ytg-item")
						.removeClass("active");
					setTimeout(function () {
						playingId = videoId;
						renderGridLayout(allVideos, shownCount);
					}, 1000);
				});

				$block.on("click", ".ultp-ytg-video img[data-video-id]", function () {
					const videoId = $(this).data("video-id");
					if (!videoId) return;

					playingId = videoId;
					renderGridLayout(allVideos, shownCount);
				});

				$loadMoreBtn.on("click", function () {
					shownCount += config.videosPerPage.lg;
					renderGridLayout(allVideos, shownCount);
				});
				// Responsive handling
				$(window).on("resize", function () {
					if (allVideos.length) {
						updateResponsiveCounts();
						renderVideos(allVideos, shownCount);
					}
				});
			}
		});
	}
})(jQuery);
