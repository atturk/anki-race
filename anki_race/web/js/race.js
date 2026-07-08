(function() {
    let timerInterval = null;
    let localState = null;

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

        // Set image paths
        document.getElementById("car-user-img").src = state.user_car_url;
        document.getElementById("car-cpu-img").src = state.cpu_car_url;

        // Animate road background texture scrolling
        const road = document.getElementById("race-road-strip");
        road.style.backgroundImage = `url('${state.road_texture_url}')`;
        road.classList.add("animating");

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
        if (!localState) return;
        
        // Update variables (position changes, card answered updates)
        localState.user_position = state.user_position;
        localState.remaining_cards = state.remaining_cards;
        localState.total_cards = state.total_cards;

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
        const overlay = document.getElementById("race-finish-overlay");
        if (!overlay || overlay.style.display !== "none") return; // already finished

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
