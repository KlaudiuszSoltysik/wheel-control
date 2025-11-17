document.addEventListener("DOMContentLoaded", () => {
    const ctx = document.getElementById('chart').getContext('2d');

    const data = {
        labels: [],
        datasets: [
            {
                label: 'Prędkość omega [rad/s]',
                data: [],
                borderColor: 'blue',
                fill: false,
                pointRadius: 0,
                tension: 0.1,
                yAxisID: 'y'
            },
            {
                label: 'Prędkość omega_zadana [rad/s]',
                data: [],
                borderColor: 'red',
                fill: false,
                pointRadius: 0,
                borderDash: [5, 5],
                tension: 0.1,
                yAxisID: 'y'
            },
            {
                label: 'Moment sterujący tau [Nm]',
                data: [],
                borderColor: 'green',
                fill: false,
                pointRadius: 0,
                tension: 0.1,
                yAxisID: 'y1'
            }
        ]
    };

    const config = {
        type: 'line',
        data: data,
        options: {
            animation: false,
            responsive: true,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Czas [s]'
                    }
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Prędkość (Omega) [rad/s]'
                    }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Moment (Tau) [Nm]'
                    },
                    grid: {
                        drawOnChartArea: false,
                    }
                }
            }
        }
    };

    const chart = new Chart(ctx, config);

    const sliders = {
        kp: document.getElementById('kpSlider'),
        ki: document.getElementById('kiSlider'),
        kd: document.getElementById('kdSlider'),
        omegaSet: document.getElementById('omegaSetSlider'),
        b: document.getElementById('bSlider'),
        disturbance: document.getElementById('disturbanceSlider'),
        mass: document.getElementById('massSlider'),
        radius: document.getElementById('radiusSlider'),
        maxMoment: document.getElementById('maxMomentSlider'),
    };
    const labels = {
        kp: document.getElementById('kpVal'),
        ki: document.getElementById('kiVal'),
        kd: document.getElementById('kdVal'),
        omegaSet: document.getElementById('omegaSetVal'),
        b: document.getElementById('bVal'),
        disturbance: document.getElementById('disturbanceVal'),
        mass: document.getElementById('massVal'),
        radius: document.getElementById('radiusVal'),
        maxMoment: document.getElementById('maxMomentVal'),
    };
    const stats = {
        settlingTime: document.getElementById('settlingTimeStat'),
        steadyStateError: document.getElementById('steadyStateErrorStat'),
        integralError: document.getElementById('integralErrorStat'),
        integralTauAbs: document.getElementById('integralTauAbsStat'),
    };
    const startButton = document.getElementById('startButton');

    const updateLabel = (name) => {
        labels[name].innerText = sliders[name].value;
    };
    for (const key in sliders) {
        sliders[key].addEventListener('input', () => updateLabel(key));
        updateLabel(key); 
    }

    const ws = new WebSocket(`ws://${window.location.host}/ws`);

    ws.onopen = () => {
        startButton.disabled = false;
        startButton.textContent = "Uruchom Symulację";
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);

            if (msg.type === 'simulation_data') {
                    const payload = msg.payload;

                    stats.settlingTime.innerText = `Settling time: ${payload.stats.settling_time.toFixed(3)} s`;
                    stats.steadyStateError.innerText = `Steady state error: ${payload.stats.steady_state_error.toFixed(4)}`;
                    stats.integralError.innerText = `Integral error: ${payload.stats.integral_error.toFixed(3)}`;
                    stats.integralTauAbs.innerText = `Total effort (Tau): ${payload.stats.integral_tau_abs.toFixed(3)}`;

                    data.labels = payload.time;
                    data.datasets[0].data = payload.omega;
                    data.datasets[1].data = new Array(payload.time.length).fill(payload.omega_set);
                    data.datasets[2].data = payload.tau;

                    chart.update();

                    console.log("Symulacja zakończona. Otrzymano dane.");
                    startButton.disabled = false;
                    startButton.textContent = "Uruchom Symulację";
            }
        }
        catch (e) {
            startButton.disabled = false;
            startButton.textContent = `Błąd symulacji: ${e.message}`;
        }
    };

    ws.onclose = () => {
        startButton.disabled = true;
        startButton.textContent = "Rozłączono";
    };

    ws.onerror = (error) => {
        startButton.disabled = true;
        startButton.textContent = "Błąd Połączenia";
    };

    startButton.addEventListener('click', () => {
        if (ws.readyState === WebSocket.OPEN) {

            const payload = {
                Kp: parseFloat(sliders.kp.value),
                Ki: parseFloat(sliders.ki.value),
                Kd: parseFloat(sliders.kd.value),
                omega_set: parseFloat(sliders.omegaSet.value),
                b: parseFloat(sliders.b.value),
                disturbance: parseFloat(sliders.disturbance.value),
                mass: parseFloat(sliders.mass.value),
                radius: parseFloat(sliders.radius.value),
                maxMoment: parseFloat(sliders.maxMoment.value)
            };

            ws.send(JSON.stringify({ 
                type: 'start_simulation', 
                payload: payload 
            }));

            startButton.disabled = true;
            startButton.textContent = "Symulacja w toku...";
        }
    });

    startButton.disabled = true;
    startButton.textContent = "Łączenie z serwerem...";
});