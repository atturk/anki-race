(function() {
    let timerInterval = null;
    let localState = null;

    function renderCustomizations(state) {
        // 1. Road style & custom texture
        const road = document.getElementById("race-road-strip");
        if (road) {
            // Hide/show minimize tab in preview
            const tab = document.getElementById("minimize-tab");
            if (tab) {
                tab.style.display = state.is_preview ? "none" : "flex";
            }

            if (state.road_style === "solid") {
                road.style.backgroundImage = "none";
                road.style.backgroundColor = state.road_solid_color || "#1e272e";
            } else {
                road.style.backgroundColor = "transparent";
                const textureUrl = state.road_texture_url || "";
                road.style.backgroundImage = `url('${textureUrl}')`;
            }
            
            // 2. Road height
            road.style.height = `${state.road_height}px`;
            const track = document.querySelector(".race-track-container");
            if (track) track.style.height = `${state.road_height}px`;
        }

        // 3. Car offsets and flips
        const cpuWrapper = document.getElementById("car-cpu-wrapper");
        const userWrapper = document.getElementById("car-user-wrapper");
        if (cpuWrapper) {
            cpuWrapper.style.top = `${state.car_cpu_offset_y}px`;
            cpuWrapper.style.transform = state.car_cpu_flip ? 'scaleX(-1)' : 'none';
        }
        if (userWrapper) {
            userWrapper.style.top = `${state.car_user_offset_y}px`;
            userWrapper.style.transform = state.car_user_flip ? 'scaleX(-1)' : 'none';
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

    window.updateRaceState = function(state) {
        if (!localState) {
            localState = state;
        } else {
            // Update variables (position changes, card answered updates)
            localState.user_position = state.user_position;
            localState.remaining_cards = state.remaining_cards;
            localState.total_cards = state.total_cards;
            localState.cpu_position = state.cpu_position;
            
            // Sync configurations
            localState.road_scrolling = state.road_scrolling;
            localState.road_height = state.road_height;
            localState.car_cpu_offset_y = state.car_cpu_offset_y;
            localState.car_user_offset_y = state.car_user_offset_y;
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
        }

        renderCustomizations(localState);
        updateProgressDisplay(localState);
        updateCarPositions(localState.user_position, localState.cpu_position);
    };

    function updateProgressDisplay(state) {
        const completed = state.total_cards - state.remaining_cards;
        const progressElem = document.getElementById("race-progress");
        if (progressElem) {
            progressElem.innerText = `${completed} / ${state.total_cards} CARTE`;
        }
    }

    function updateCarPositions(userPos, cpuPos) {
        const userWrapper = document.getElementById("car-user-wrapper");
        const cpuWrapper = document.getElementById("car-cpu-wrapper");
        
        if (userWrapper && cpuWrapper) {
            // Calc left positions (max 85% of track width to leave room for finish flag)
            userWrapper.style.left = `calc(${userPos}% * 0.85)`;
            cpuWrapper.style.left = `calc(${cpuPos}% * 0.85)`;
        }
    }

    function updateGameTick() {
        if (!localState || !localState.race_in_progress) return;

        // Calculate elapsed time
        const now = Date.now() / 1000;
        const elapsed = Math.max(0, now - localState.start_time);
        
        // Display timer value
        const minutes = Math.floor(elapsed / 60);
        const seconds = Math.floor(elapsed % 60);
        const timeStr = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        
        const timeValElem = document.getElementById("race-time-value");
        if (timeValElem) timeValElem.innerText = timeStr;

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
                msg = "L'inseguitore ti ha raggiunto! Fai più in fretta la prossima volta!";
            } else if (userPos >= 100.0) {
                isGameOver = true;
                isVictory = true;
                msg = "Sei sfuggito all'inseguitore completando tutto il mazzo!";
            }
        } else {
            if (userPos >= 100.0) {
                isGameOver = true;
                isVictory = true;
                msg = "Complimenti! Hai battuto la CPU tagliando il traguardo per primo!";
            } else if (cpuPos >= 100.0) {
                isGameOver = true;
                isVictory = false;
                msg = "La CPU ha tagliato il traguardo prima di te. Riprova!";
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



    // Auto-launch trigger to request initial state from Python
    setTimeout(() => {
        pycmd("anki_race_get_initial_state");
        
        const tab = document.getElementById("minimize-tab");
        if (tab) {
            tab.onclick = function() {
                const isMinimized = document.body.classList.toggle("minimized");
                pycmd("anki_race_toggle_minimize:" + isMinimized);
            };
        }
    }, 50);
})();
