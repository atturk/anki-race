(function() {
    // 1. Check if state exists
    const state = window.ankiRaceState;
    if (!state || !state.race_in_progress) {
        // If race is not active, hide the container or don't render
        const container = document.getElementById("anki-race-container");
        if (container) container.style.display = "none";
        return;
    }

    // 2. Fetch and render HTML
    const container = document.getElementById("anki-race-container");
    if (!container) return;

    fetch("/_addons/anki_race/web/index.html")
        .then(response => {
            if (!response.ok) throw new Error("Could not load race HTML");
            return response.text();
        })
        .then(html => {
            container.innerHTML = html;
            initializeRace(state);
        })
        .catch(err => {
            console.error("AnkiRace Error:", err);
        });

    let timerInterval = null;

    function initializeRace(state) {
        // Set static properties
        document.getElementById("race-deck-name").innerText = state.deck_name || "Mazzo";
        document.getElementById("race-mode").innerText = state.mode.toUpperCase();
        
        // Apply color code for modes
        const modeBadge = document.getElementById("race-mode");
        if (state.mode === "fuga") {
            modeBadge.style.backgroundColor = "#e67e22";
        } else {
            modeBadge.style.backgroundColor = "#e74c3c";
        }

        // Set image sources
        document.getElementById("car-user-img").src = state.user_car_url;
        document.getElementById("car-cpu-img").src = state.cpu_car_url;

        // Set road background and animate it
        const road = document.getElementById("race-road-strip");
        road.style.backgroundImage = `url('${state.road_texture_url}')`;
        road.classList.add("animating");

        // Calculate completed cards text
        const completed = state.total_cards - state.remaining_cards;
        document.getElementById("race-progress").innerText = `${completed} / ${state.total_cards} CARTE`;

        // Update positions immediately
        updateCarPositions(state.user_position, state.cpu_position);

        // Start live game loop (100ms ticks)
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(() => {
            updateGameLoop(state);
        }, 100);

        // Intercept key events when game over overlay is shown
        window.addEventListener("keydown", blockAnkiKeys, true);
    }

    function updateCarPositions(userPos, cpuPos) {
        const userWrapper = document.getElementById("car-user-wrapper");
        const cpuWrapper = document.getElementById("car-cpu-wrapper");
        
        if (userWrapper && cpuWrapper) {
            // Map 0-100% to track (leaves ~85% of road width to account for car width and finish line)
            userWrapper.style.left = `calc(${userPos}% * 0.85)`;
            cpuWrapper.style.left = `calc(${cpuPos}% * 0.85)`;
        }
    }

    function updateGameLoop(state) {
        if (!state.race_in_progress) return;

        // Compute elapsed time
        const now = Date.now() / 1000;
        const elapsed = Math.max(0, now - state.start_time);
        
        // Format time display
        const minutes = Math.floor(elapsed / 60);
        const seconds = Math.floor(elapsed % 60);
        const timeStr = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        const timeValElem = document.getElementById("race-time-value");
        if (timeValElem) timeValElem.innerText = timeStr;

        // Compute CPU Position based on mode
        let cpuPos = 0;
        const totalSeconds = state.chosen_time * 60;
        
        if (state.mode === "fuga") {
            // Fuga (Inseguimento): CPU starts at 0% (user has headstart e.g. based on card position or constant)
            // CPU speeds up over time: acceleration formula
            // position = 0.5 * accel * t^2
            // We set acceleration so it catches user (starting at 35%) at totalSeconds if user doesn't advance
            const accel = 100.0 / (totalSeconds * totalSeconds);
            cpuPos = Math.min(100.0, 0.5 * accel * elapsed * elapsed * 2); // multiplied by 2 for challenge
        } else {
            // Normale: CPU travels at constant speed to reach 100% at totalSeconds
            cpuPos = Math.min(100.0, (elapsed / totalSeconds) * 100.0);
        }

        // User Position is static (calculated in Python per card)
        const userPos = state.user_position;

        // Update positions visually
        updateCarPositions(userPos, cpuPos);

        // Check race finish conditions
        checkRaceResult(state, userPos, cpuPos, elapsed, timeStr);
    }

    function checkRaceResult(state, userPos, cpuPos, elapsed, timeStr) {
        const overlay = document.getElementById("race-finish-overlay");
        if (!overlay || overlay.style.display !== "none") return; // already triggered

        let isGameOver = false;
        let isVictory = false;
        let msg = "";

        if (state.mode === "fuga") {
            // Fuga: User loses if CPU catches them (cpuPos >= userPos)
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
            // Normale: First to 100% wins
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
            // Stop road animation
            const road = document.getElementById("race-road-strip");
            if (road) road.classList.remove("animating");

            // Stop game loop timer
            if (timerInterval) clearInterval(timerInterval);

            // Populate overlay metrics
            document.getElementById("overlay-title").innerText = isVictory ? "VITTORIA!" : "GAME OVER";
            document.getElementById("overlay-title").style.color = isVictory ? "#2ecc71" : "#e74c3c";
            document.getElementById("overlay-icon").innerText = isVictory ? "🏆" : "💥";
            document.getElementById("stat-time").innerText = timeStr;
            
            const completed = state.total_cards - state.remaining_cards;
            document.getElementById("stat-cards").innerText = `${completed} / ${state.total_cards}`;
            document.getElementById("overlay-message").innerText = msg;

            // Trigger Python side to end the race status
            pycmd("anki_race_finished");

            // Show overlay
            overlay.style.display = "flex";
        }
    }

    function blockAnkiKeys(e) {
        const overlay = document.getElementById("race-finish-overlay");
        if (overlay && overlay.style.display !== "none") {
            // Block event from reaching Anki keys (like Spacebar or 1-4 keys)
            e.stopPropagation();
            e.preventDefault();
        }
    }

    // Global function to close overlay and clean event listeners
    window.closeRaceOverlay = function() {
        const overlay = document.getElementById("race-finish-overlay");
        if (overlay) overlay.style.display = "none";
        window.removeEventListener("keydown", blockAnkiKeys, true);
    };
})();
