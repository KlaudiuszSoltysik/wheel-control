document.addEventListener("DOMContentLoaded", () => {

    // Inicjalizacja chartow Chart.js
    const ctx = document.getElementById('chart').getContext('2d');
    const ctxFuzzy = document.getElementById('chartFuzzy').getContext('2d');

    // Funkcja pomocnicza do tworzenia wykresow Chart.js
    const createChart = (ctx, labelsY, labelsY1) => new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: labelsY.concat(labelsY1)
        },
        options: {
            animation: false,
            responsive: true,
            scales: {
                x: { title: { display: true, text: 'Czas [s]' } },
                y: { 
                    type: 'linear', 
                    position: 'left',
                    title: { display: true, text: 'Prędkość (Omega) [rad/s]' }
                },
                y1: { 
                    type: 'linear', 
                    position: 'right',
                    title: { display: true, text: 'Moment (Tau) [Nm]' },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });

    // Tworzyymy wykres PID
    const chart = createChart(ctx, [
        { label: 'Prędkość omega [rad/s]', data: [], borderColor: 'blue', fill: false, pointRadius: 0, tension: 0.1, yAxisID: 'y' },
        { label: 'Prędkość omega_zadana [rad/s]', data: [], borderColor: 'red', fill: false, pointRadius: 0, borderDash: [5, 5], tension: 0.1, yAxisID: 'y' }
    ], [
        { label: 'Moment sterujący tau [Nm]', data: [], borderColor: 'green', fill: false, pointRadius: 0, tension: 0.1, yAxisID: 'y1' }
    ]);

    // Tworzyymy wykres Fuzzy
    const chartFuzzy = createChart(ctxFuzzy, [
        { label: 'ω_fuzzy [rad/s]', data: [], borderColor: 'purple', fill: false, pointRadius: 0, tension: 0.1, yAxisID: 'y' },
        { label: 'Prędkość omega_zadana [rad/s]', data: [], borderColor: 'red', fill: false, pointRadius: 0, borderDash: [5, 5], tension: 0.1, yAxisID: 'y' }
    ], [
        { label: 'tau_fuzzy [Nm]', data: [], borderColor: 'orange', fill: false, pointRadius: 0, tension: 0.1, yAxisID: 'y1' }
    ]);

    // Tworzymy suwaki
    const sliders = {
        kp: kpSlider, 
        ki: kiSlider, 
        kd: kdSlider, 
        omegaSet: omegaSetSlider,
        b: bSlider, 
        disturbance: disturbanceSlider, 
        mass: massSlider,
        radius: radiusSlider, 
        maxMoment: maxMomentSlider
    };

    // Tworzymy elementy do wyswietlania zawartosci suwakow
    const labels = {
        kp: kpVal, 
        ki: kiVal, 
        kd: kdVal, 
        omegaSet: omegaSetVal,
        b: bVal, 
        disturbance: disturbanceVal, 
        mass: massVal,
        radius: radiusVal, 
        maxMoment: maxMomentVal
    };

    // // Tworzymy elementy do wyswietlania statystyk
    // const stats = {
    //     settlingTime: settlingTimeStat,
    //     steadyStateError: steadyStateErrorStat,
    //     integralError: integralErrorStat,
    //     integralTauAbs: integralTauAbsStat
    // };

    // // Tworzymy elementy do wyswietlania statystyk fuzzy
    // const statsFuzzy = {
    //     settlingTime: settlingTimeStatFuzzy,
    //     steadyStateError: steadyStateErrorStatFuzzy,
    //     integralError: integralErrorStatFuzzy,
    //     integralTauAbs: integralTauAbsStatFuzzy
    // };

    // Obsluga zmiany wartosci wszystkich suwakow na raz
    Object.keys(sliders).forEach(key => {
        sliders[key].addEventListener('input', () => labels[key].innerText = sliders[key].value);
        labels[key].innerText = sliders[key].value;
    });

    // Inicjalizacja WebSocket
    const ws = new WebSocket(`ws://${window.location.host}/ws`);

    // Co ma sie stac po roznych zdarzeniach WebSocket
    ws.onopen = () => {
        startButton.disabled = false;
        startButton.textContent = "Uruchom Symulację";
    };

    // Ta funkcja uruchamia sie gdy serwer wysle dane symulacji
    ws.onmessage = ({ data }) => {
        try {
            const { type, payload } = JSON.parse(data);
            if (type !== 'simulation_data') return;

            // stats.settlingTime.innerText = `Settling time: ${payload.stats.settling_time.toFixed(3)} s`;
            // stats.steadyStateError.innerText = `Steady state error: ${payload.stats.steady_state_error.toFixed(4)}`;
            // stats.integralError.innerText = `Integral error: ${payload.stats.integral_error.toFixed(3)}`;
            // stats.integralTauAbs.innerText = `Total effort (Tau): ${payload.stats.integral_tau_abs.toFixed(3)}`;

            // statsFuzzy.settlingTime.innerText = `Settling time (Fuzzy): ${payload.stats_fuzzy.settling_time.toFixed(3)} s`;
            // statsFuzzy.steadyStateError.innerText = `Steady state error (Fuzzy): ${payload.stats_fuzzy.steady_state_error.toFixed(4)}`;
            // statsFuzzy.integralError.innerText = `Integral error (Fuzzy): ${payload.stats_fuzzy.integral_error.toFixed(3)}`;
            // statsFuzzy.integralTauAbs.innerText = `Total effort (Tau Fuzzy): ${payload.stats_fuzzy.integral_tau_abs.toFixed(3)}`;

            chart.data.labels = payload.time;
            chart.data.datasets[0].data = payload.omega;
            chart.data.datasets[1].data = new Array(payload.time.length).fill(payload.omega_set);
            chart.data.datasets[2].data = payload.tau;
            chart.update();

            chartFuzzy.data.labels = payload.time;
            chartFuzzy.data.datasets[0].data = payload.omega_fuzzy;
            chartFuzzy.data.datasets[1].data = new Array(payload.time.length).fill(payload.omega_set);
            chartFuzzy.data.datasets[2].data = payload.tau_fuzzy;
            chartFuzzy.update();

            startButton.disabled = false;
            startButton.textContent = "Uruchom Symulację";
        } catch (e) {
            startButton.disabled = false;
            startButton.textContent = `Błąd symulacji: ${e.message}`;
        }
    };

    // Zdarzenia zamkniecia polaczenia WebSocket
    ws.onclose = () => {
        startButton.disabled = true;
        startButton.textContent = "Rozłączono";
    };

    // Obsługa bledow WebSocket
    ws.onerror = () => {
        startButton.disabled = true;
        startButton.textContent = "Błąd Połączenia";
    };

    // Obsługa kliknięcia przycisku 'uruchom symulacje'
    startButton.addEventListener('click', () => {
        if (ws.readyState !== WebSocket.OPEN) return;

        const payload = Object.fromEntries(
            Object.entries(sliders).map(([k, el]) => [k === "omegaSet" ? "omega_set" : k, parseFloat(el.value)])
        );

        ws.send(JSON.stringify({ type: 'start_simulation', payload }));

        startButton.disabled = true;
        startButton.textContent = "Symulacja w toku...";
    });

    startButton.disabled = true;
    startButton.textContent = "Łączenie z serwerem...";
});