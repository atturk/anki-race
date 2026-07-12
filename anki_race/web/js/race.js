(function() {
    let timerInterval = null;
    let localState = null;

    function renderCustomizations(state) {
        // 1. Road style & custom texture
        const road = document.getElementById("race-road-strip");
        if (road) {
            if (state.road_style === "solid") {
                road.style.backgroundImage = "none";
                road.style.backgroundColor = state.road_solid_color || "#1e272e";
            } else {
                road.style.backgroundColor = "transparent";
                const textureUrl = state.road_texture_url || "";
                road.style.backgroundImage = `url('${textureUrl}')`;
            }
            if (state.road_scrolling) {
                road.classList.add("animating");
            } else {
                road.classList.remove("animating");
            }
            if (state.race_paused) {
                road.classList.add("paused");
            } else {
                road.classList.remove("paused");
            }
            
            // 2. Road height
            road.style.height = `${state.road_height}px`;
            const track = document.querySelector(".race-track-container");
            if (track) track.style.height = `${state.road_height}px`;
        }

        // Decorations rendering (in-road overlay)
        renderDecorations(state);

        // 3. Car offsets, sizes and flips
        const cpuWrapper = document.getElementById("car-cpu-wrapper");
        const userWrapper = document.getElementById("car-user-wrapper");
        if (cpuWrapper) {
            cpuWrapper.style.top = `${state.car_cpu_offset_y}px`;
            const cpuScaleX = state.car_cpu_flip ? -1 : 1;
            cpuWrapper.style.transform = `translateY(-50%) scaleX(${cpuScaleX})`;
            const cpuSize = state.car_cpu_size || 32;
            cpuWrapper.style.width = `${cpuSize}px`;
            cpuWrapper.style.height = `${cpuSize}px`;
            
            const cpuImg = document.getElementById("car-cpu-img");
            const cpuEmoji = document.getElementById("car-cpu-emoji");
            if (cpuImg) {
                cpuImg.style.maxHeight = `${cpuSize}px`;
                cpuImg.style.maxWidth = `${cpuSize}px`;
            }
            if (cpuEmoji) {
                cpuEmoji.style.fontSize = `${cpuSize * 0.75}px`;
                cpuEmoji.style.lineHeight = `${cpuSize}px`;
            }
        }
        if (userWrapper) {
            userWrapper.style.top = `${state.car_user_offset_y}px`;
            const userScaleX = state.car_user_flip ? -1 : 1;
            userWrapper.style.transform = `translateY(-50%) scaleX(${userScaleX})`;
            const userSize = state.car_user_size || 32;
            userWrapper.style.width = `${userSize}px`;
            userWrapper.style.height = `${userSize}px`;
            
            const userImg = document.getElementById("car-user-img");
            const userEmoji = document.getElementById("car-user-emoji");
            const nitroFire = document.getElementById("nitro-fire");
            if (userImg) {
                userImg.style.maxHeight = `${userSize}px`;
                userImg.style.maxWidth = `${userSize}px`;
            }
            if (userEmoji) {
                userEmoji.style.fontSize = `${userSize * 0.75}px`;
                userEmoji.style.lineHeight = `${userSize}px`;
            }
            if (nitroFire) {
                nitroFire.style.fontSize = `${userSize * 0.75}px`;
                nitroFire.style.lineHeight = `${userSize}px`;
                if (state.car_user_flip) {
                    nitroFire.style.left = "auto";
                    nitroFire.style.right = "-65%";
                    nitroFire.style.transform = "translateY(-50%) rotate(90deg)";
                } else {
                    nitroFire.style.left = "-65%";
                    nitroFire.style.right = "auto";
                    nitroFire.style.transform = "translateY(-50%) rotate(-90deg)";
                }
            }
        }
 
        // 4. CPU Car Type rendering
        const cpuImg = document.getElementById("car-cpu-img");
        const cpuEmoji = document.getElementById("car-cpu-emoji");
        if (cpuImg && cpuEmoji) {
            if (state.car_cpu_type === "emoji") {
                cpuImg.style.display = "none";
                cpuEmoji.style.display = "inline-block";
                cpuEmoji.innerText = state.car_cpu_emoji || "🚓";
            } else {
                cpuEmoji.style.display = "none";
                cpuImg.style.display = "inline-block";
                cpuImg.src = state.cpu_car_url;
            }
        }
 
        // 5. User Car Type rendering
        const userImg = document.getElementById("car-user-img");
        const userEmoji = document.getElementById("car-user-emoji");
        if (userImg && userEmoji) {
            if (state.car_user_type === "emoji") {
                userImg.style.display = "none";
                userEmoji.style.display = "inline-block";
                userEmoji.innerText = state.car_user_emoji || "🏎️";
            } else {
                userEmoji.style.display = "none";
                userImg.style.display = "inline-block";
                userImg.src = state.user_car_url;
            }
        }
    }

    function renderDecorations(state) {
        const container = document.getElementById("race-decorations");
        if (!container) return;
        
        if (!state.decor_enabled) {
            container.style.display = "none";
            return;
        }
        
        container.style.display = "block";
        container.style.top = `${state.decor_y}px`;
        container.style.height = `${state.decor_size}px`;
        
        const marquee = document.getElementById("decor-marquee");
        const group1 = document.getElementById("decor-group-1");
        const group2 = document.getElementById("decor-group-2");
        if (!marquee || !group1 || !group2) return;
        
        if (state.decor_replicate) {
            group2.style.display = "flex";
            marquee.style.backgroundImage = "none";
            marquee.classList.remove("animating-bg");
            
            let itemHtml = "";
            if (state.decor_type === "emoji") {
                const val = state.decor_emoji || "🌲";
                itemHtml = `<span class="decor-item" style="font-size: ${state.decor_size}px; margin-right: ${state.decor_spacer}px;">${val}</span>`;
            } else {
                const url = state.decor_texture_url || "";
                if (url) {
                    itemHtml = `<img class="decor-item" src="${url}" style="height: ${state.decor_size}px; width: auto; margin-right: ${state.decor_spacer}px;" />`;
                } else {
                    itemHtml = `<div class="decor-item" style="height: ${state.decor_size}px; width: ${state.decor_size}px; background-color: #ffffff; margin-right: ${state.decor_spacer}px;"></div>`;
                }
            }
            
            // Calculate a safe repetition count based on window width to cover the screen entirely
            const minItemWidth = Math.max(5, state.decor_size + state.decor_spacer);
            const count = Math.ceil((window.innerWidth * 1.5) / minItemWidth) + 10;
            
            let groupHtml = "";
            for (let i = 0; i < count; i++) {
                groupHtml += itemHtml;
            }
            
            group1.innerHTML = groupHtml;
            group2.innerHTML = groupHtml;
            
            marquee.style.width = "max-content";
            marquee.style.transform = "";
            marquee.style.position = "";
            marquee.style.left = "";
            
            if (state.decor_scrolling) {
                marquee.style.animation = "none";
                void marquee.offsetWidth; // trigger reflow
                marquee.style.animation = "";
                
                const speedVal = state.decor_speed || 2;
                const duration = 32 - (speedVal * 3);
                marquee.style.setProperty("--decor-duration", `${duration}s`);
                marquee.classList.add("animating");
            } else {
                marquee.classList.remove("animating");
            }
            if (state.race_paused) {
                marquee.classList.add("paused");
            } else {
                marquee.classList.remove("paused");
            }
        } else {
            marquee.style.backgroundImage = "none";
            marquee.classList.remove("animating-bg");
            marquee.classList.remove("animating");
            group2.style.display = "none";
            group2.innerHTML = "";
            
            let itemHtml = "";
            if (state.decor_type === "emoji") {
                const val = state.decor_emoji || "🌲";
                itemHtml = `<span class="decor-item" style="font-size: ${state.decor_size}px;">${val}</span>`;
            } else {
                const url = state.decor_texture_url || "";
                if (url) {
                    itemHtml = `<img class="decor-item" src="${url}" style="height: ${state.decor_size}px; width: auto;" />`;
                } else {
                    itemHtml = `<div class="decor-item" style="height: ${state.decor_size}px; width: ${state.decor_size}px; background-color: #ffffff;"></div>`;
                }
            }
            group1.innerHTML = itemHtml;
            
            marquee.style.transform = "none";
            marquee.style.position = "absolute";
            marquee.style.left = `${state.decor_x}%`;
        }
    }

    // Define globally accessible API for Python to push updates
    window.initializeRace = function(state) {
        localState = state;

        // Set static properties
        const deckElem = document.getElementById("race-deck-name");
        if (deckElem) deckElem.innerText = state.deck_name || "Mazzo";
        
        const modeBadge = document.getElementById("race-mode");
        if (modeBadge) {
            modeBadge.innerText = state.mode.toUpperCase();
            if (state.mode === "fuga") {
                modeBadge.style.backgroundColor = "#e67e22";
            } else {
                modeBadge.style.backgroundColor = "#e74c3c";
            }
        }

        // Set background road image
        const road = document.getElementById("race-road-strip");
        if (road) road.style.backgroundImage = `url('${state.road_texture_url}')`;

        renderCustomizations(state);

        // Render card numbers
        updateProgressDisplay(state);

        // Update wrappers
        updateCarPositions(state.user_position, state.cpu_position);

        // Clear existing intervals
        if (timerInterval) clearInterval(timerInterval);
        
        // Start live rendering (100ms interval for CPU smooth animation and timer)
        timerInterval = setInterval(() => {
            updateGameTick();
        }, 100);
    };
    
    window.stopRaceBar = function() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
        if (localState) {
            localState.race_in_progress = false;
        }
    };

    window.updateRaceState = function(state) {
        if (!localState) {
            localState = state;
        } else {
            // Update variables (position changes, card answered updates)
            localState.user_position = state.user_position;
            localState.remaining_cards = state.remaining_cards;
            localState.total_cards = state.total_cards;
            localState.cpu_position = state.cpu_position;
            localState.race_paused = state.race_paused;
            localState.elapsed_before_pause = state.elapsed_before_pause;
            localState.start_time = state.start_time;
            
            // Sync configurations
            localState.road_scrolling = state.road_scrolling;
            localState.road_height = state.road_height;
            localState.car_cpu_offset_y = state.car_cpu_offset_y;
            localState.car_cpu_size = state.car_cpu_size;
            localState.car_user_offset_y = state.car_user_offset_y;
            localState.car_user_size = state.car_user_size;
            localState.car_cpu_type = state.car_cpu_type;
            localState.car_cpu_emoji = state.car_cpu_emoji;
            localState.car_cpu_flip = state.car_cpu_flip;
            localState.car_user_type = state.car_user_type;
            localState.car_user_emoji = state.car_user_emoji;
            localState.car_user_flip = state.car_user_flip;
            localState.user_car_url = state.user_car_url;
            localState.cpu_car_url = state.cpu_car_url;
            localState.road_style = state.road_style;
            localState.road_solid_color = state.road_solid_color;
            localState.road_image_file = state.road_image_file;
            localState.road_texture_url = state.road_texture_url;
            localState.is_preview = state.is_preview;
            localState.decor_enabled = state.decor_enabled;
            localState.decor_type = state.decor_type;
            localState.decor_emoji = state.decor_emoji;
            localState.decor_image_file = state.decor_image_file;
            localState.decor_texture_url = state.decor_texture_url;
            localState.decor_y = state.decor_y;
            localState.decor_size = state.decor_size;
            localState.decor_replicate = state.decor_replicate;
            localState.decor_spacer = state.decor_spacer;
            localState.decor_x = state.decor_x;
            localState.decor_scrolling = state.decor_scrolling;
            localState.decor_speed = state.decor_speed;
            localState.nitro_enabled = state.nitro_enabled;
            localState.nitro_cards = state.nitro_cards;
            localState.nitro_active = state.nitro_active;
        }

        renderCustomizations(localState);
        updateProgressDisplay(localState);
        updateCarPositions(localState.user_position, localState.cpu_position);

        // Update Nitro Fire visibility
        const nitroFire = document.getElementById("nitro-fire");
        if (nitroFire) {
            if (localState.nitro_enabled) {
                if (localState.is_preview) {
                    // Preview shows it constitutively
                    nitroFire.style.display = "inline-block";
                    nitroFire.classList.remove("nitro-blink");
                } else if (state.nitro_active) {
                    // Game mode triggers flashing effect and hides after animation completes (0.8s)
                    nitroFire.style.display = "inline-block";
                    nitroFire.classList.add("nitro-blink");
                    if (window.nitroTimeout) clearTimeout(window.nitroTimeout);
                    window.nitroTimeout = setTimeout(() => {
                        nitroFire.style.display = "none";
                        nitroFire.classList.remove("nitro-blink");
                    }, 800);
                } else {
                    nitroFire.style.display = "none";
                    nitroFire.classList.remove("nitro-blink");
                }
            } else {
                nitroFire.style.display = "none";
                nitroFire.classList.remove("nitro-blink");
            }
        }
    };

    function updateProgressDisplay(state) {
        const completed = state.total_cards - state.remaining_cards;
        const progressElem = document.getElementById("race-progress");
        if (progressElem) {
            progressElem.innerText = `${completed} / ${state.total_cards} CARDS`;
        }
    }

    function updateCarPositions(userPos, cpuPos) {
        const userWrapper = document.getElementById("car-user-wrapper");
        const cpuWrapper = document.getElementById("car-cpu-wrapper");
        
        if (userWrapper && cpuWrapper && localState) {
            const userSize = localState.car_user_size || 32;
            const cpuSize = localState.car_cpu_size || 32;
            
            // Align left edge of car wrapper at 0%, right edge at 100%
            userWrapper.style.left = `calc(${userPos}% - ${(userPos / 100) * userSize}px)`;
            cpuWrapper.style.left = `calc(${cpuPos}% - ${(cpuPos / 100) * cpuSize}px)`;
        }
    }

    function updateGameTick() {
        if (!localState || !localState.race_in_progress) return;

        // Calculate elapsed time
        let elapsed = localState.elapsed_before_pause || 0;
        if (!localState.race_paused) {
            const now = Date.now() / 1000;
            elapsed += Math.max(0, now - localState.start_time);
        }
        
        // Display timer value
        const minutes = Math.floor(elapsed / 60);
        const seconds = Math.floor(elapsed % 60);
        const timeStr = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        
        const timeValElem = document.getElementById("race-time-value");
        if (timeValElem) timeValElem.innerText = timeStr;

        if (localState.race_paused) return;

        // Calculate CPU Position dynamically (constant speed to reach 100% in chosen_time)
        const totalSeconds = localState.chosen_time * 60;
        const cpuPos = Math.min(100.0, (elapsed / totalSeconds) * 100.0);

        localState.cpu_position = cpuPos;

        // Update positions visually
        updateCarPositions(localState.user_position, cpuPos);

        // Check for victory or game over
        checkRaceEndConditions(elapsed, timeStr);
    }

    function checkRaceEndConditions(elapsed, timeStr) {
        if (!localState || !localState.race_in_progress) return;

        let isGameOver = false;
        let isVictory = false;
        let msg = "";

        const userPos = localState.user_position;
        const cpuPos = localState.cpu_position;

        if (localState.mode === "fuga") {
            if (cpuPos >= userPos && userPos < 100.0) {
                isGameOver = true;
                isVictory = false;
                msg = "The pursuer caught up to you! Speed up next time!";
            } else if (userPos >= 100.0) {
                isGameOver = true;
                isVictory = true;
                msg = "You escaped the pursuer by completing the whole deck!";
            }
        } else {
            if (userPos >= 100.0) {
                isGameOver = true;
                isVictory = true;
                msg = "Congratulations! You beat the CPU and crossed the finish line first!";
            } else if (cpuPos >= 100.0) {
                isGameOver = true;
                isVictory = false;
                msg = "The CPU crossed the finish line before you. Try again!";
            }
        }

        if (isGameOver) {
            // Stop update loop
            if (timerInterval) clearInterval(timerInterval);
            localState.race_in_progress = false;

            // Notify Python that the game finished with victory/defeat
            pycmd("anki_race_finished:" + (isVictory ? "victory" : "defeat"));
        }
    }



    // Re-render customizations on window resize to ensure no blank spaces appear
    window.addEventListener("resize", () => {
        if (localState) {
            renderCustomizations(localState);
        }
    });

    // Auto-launch trigger to request initial state from Python
    setTimeout(() => {
        pycmd("anki_race_get_initial_state");
    }, 50);
})();
