import json
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request

# Uruchamiamy aplikacje FastAPI
app = FastAPI()

# Konfiguracja plikow Jinja2
app.mount("/static", StaticFiles(directory="static"), name="static")
static = Jinja2Templates(directory="static")

# Gdy ktos wejdzie na strone glowna, wyswietlamy index.html
@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    return static.TemplateResponse("index.html", {"request": request})

# Trojkatne funkcje przynaleznosci rozmytej [-1, 1], czyli jak bardzo wartosc x nalezy do zbiorow NB, NS, Z, PS, PB - zwraca slownik
# - NB: Negative Big
# - NS: Negative Small
# - Z: Zero
# - PS: Positive Small
# - PB: Positive Big
def fuzzy_membership(x):
    return {
        "NB": max(min((x + 1.0) / -0.5, 1), 0),
        "NS": max(min((x + 1.0) / 0.5, (0.0 - x) / 0.5), 0),
        "Z":  max(1 - abs(x) / 0.5, 0),
        "PS": max(min((x - 0.0) / 0.5, (1.0 - x) / 0.5), 0),
        "PB": max(min((x - 0.5) / 0.5, 1), 0)
    }

# Funkcja regulatora rozmytego
def fuzzy_controller(e, de):
    # Rozpisanie macierzy 5x5 regul rozmytych
    rules = {
        ("NB", "NB"): -1.0, # Jesli blad jest NB i zmiana bledu jest NB, to tau jest -1.0
        ("NB", "NS"): -1.0, # Jesli blad jest NB i zmiana bledu jest NS, to tau jest -1.0
        ("NB", "Z"):  -1.0, # Jesli blad jest NB i zmiana bledu jest Z, to tau jest -1.0
        ("NB", "PS"): -0.5, # Jesli blad jest NB i zmiana bledu jest PS, to tau jest -0.5
        ("NB", "PB"):  0.0, # Jesli blad jest NB i zmiana bledu jest PB, to tau jest 0.0

        ("NS", "NB"): -1.0,
        ("NS", "NS"): -0.5,
        ("NS", "Z"):  -0.5,
        ("NS", "PS"):  0.0,
        ("NS", "PB"):  0.5,

        ("Z",  "NB"): -1.0,
        ("Z",  "NS"): -0.5,
        ("Z",  "Z"):   0.0,
        ("Z",  "PS"):  0.5,
        ("Z",  "PB"):  1.0,

        ("PS", "NB"): -0.5,
        ("PS", "NS"):  0.0,
        ("PS", "Z"):   0.5,
        ("PS", "PS"):  0.5,
        ("PS", "PB"):  1.0,

        ("PB", "NB"):  0.0,
        ("PB", "NS"):  0.5,
        ("PB", "Z"):   1.0,
        ("PB", "PS"):  1.0,
        ("PB", "PB"):  1.0,
    }

    # Obliczenie wartosci przynaleznosci dla e i de
    # Output to slownik z wartosciami przynaleznosci do kazdego zbioru
    e_sets = fuzzy_membership(e)
    de_sets = fuzzy_membership(de)

    num = 0.0
    den = 0.0

    # 
    for key, out_val in rules.items():
        # Stopien aktywacji pojedynczej reguly
        u = min(e_sets[key[0]], de_sets[key[1]])

        # Stopien aktywacji * wartosc wyjscia reguly - mniejsza wartosc z trojkatnej funkcji przynaleznosci razy wartosc wyjscia dla danej reguly
        num += u * out_val

        # Suma stopni aktywacji
        den += u                                    

    # Srednia wazona - defuzywikacja
    if den == 0:
        return 0
    else:
        return num / den

# Kanal Websocket do komunikacji z klientem
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        try:
            # Czekamy na wiadomosc JSON od klienta
            msg = await websocket.receive_text()
            data = json.loads(msg)

            # Jezeli otrzymamy polecenie "start_simulation", uruchamiamy symulacje
            if data.get('type') == 'start_simulation':
                params = data.get('payload', {})

                # Parametry symulacji
                m = params.get("mass", 1.0)
                r = params.get("radius", 0.5)
                I = max(0.5 * m * r**2, 1e-6)
                setpoint = params.get("omega_set", 0.0)

                # Inicjalizacja list na dane do wykresu PID
                time_data = []
                omega_data = []
                tau_data = []

                # Inicjalizacja list na dane do wykresu Fuzzy
                omega_fuzzy_data = []
                tau_fuzzy_data = []

                # Inicjalizacja zmiennych PID
                omega = 0.0
                integral = 0.0
                prev_error = 0.0
                dt = 0.001
                time = 0.0

                # Inicjalizacja zmiennych Fuzzy
                omega_fuzzy = 0.0
                prev_error_fuzzy = 0.0

                # Dodanie pierwszego punktu PID (czas 0)
                time_data.append(time)
                omega_data.append(omega)
                tau_data.append(0)

                # Dodanie pierwszego punktu Fuzzy (czas 0)
                omega_fuzzy_data.append(omega_fuzzy)
                tau_fuzzy_data.append(0)

                # Zmienne do statystyk czasowych
                integral_error_abs = 0.0
                integral_error_abs_fuzzy = 0.0

                # Glowna petla regulacji PID + Fuzzy
                max_iterations = 5000
                for _ in range(max_iterations):
                    max_tau = params.get("maxMoment", 0.5)

                    ###########################################################################################
                    # Regulator PID
                    ###########################################################################################
                    error = setpoint - omega                # obliczenie bledu
                    integral += error * dt                  # czlon calkujacy
                    derivative = (error - prev_error) / dt  # czlon rozniczkujacy
                    prev_error = error                      # aktualizacja poprzedniego bledu

                    # Obliczanie sterowania PID
                    tau_pid = (
                        params.get("kp", 0.0) * error +
                        params.get("ki", 0.0) * integral +
                        params.get("kd", 0.0) * derivative
                    )

                    # Ograniczanie sterowania do przedzialu [-max_tau, max_tau]
                    tau_clamped = max(-max_tau, min(max_tau, tau_pid))

                    # Rownanie dynamiki ukladu - wyliczamy predkosc katowa po zastosowaniu sterowania PID
                    domega = (tau_clamped - params.get("b", 0.0) * omega - params.get("disturbance", 0.0)) / I   # dw/dt = (tau - b*w - disturbance) / I
                    omega += domega * dt

                    # Calkowanie bledu bezwzglednego dla PID
                    integral_error_abs += abs(setpoint - omega) * dt                                                                     # w = w(t) + dw/dt * dt

                    # Zapis danych do wykresu oraz statystyk
                    time += dt       
                    time_data.append(round(time, 3))
                    omega_data.append(omega)
                    tau_data.append(tau_clamped)

                    ###########################################################################################
                    # Regulator rozmyty
                    ###########################################################################################
                    e_norm = max(-1, min(1, (setpoint - omega_fuzzy) / (abs(setpoint) + 1e-5))) # normalizacja bledu do przedzialu [-1, 1]
                    de_norm = e_norm - prev_error_fuzzy                                         # Pochodna bledu
                    de_norm = max(-1, min(1, de_norm))                                          # normalizacja pochodnej bledu do przedzialu [-1, 1]
                    prev_error_fuzzy = e_norm                                                   # aktualizacja poprzedniego bledu

                    # Obliczanie sterowania rozmytego
                    tau_fuzzy = fuzzy_controller(e_norm, de_norm) * max_tau

                    # Ograniczanie sterowania do przedzialu [-max_tau, max_tau]
                    tau_fuzzy = max(-max_tau, min(max_tau, tau_fuzzy))

                    # Rownanie dynamiki ukladu - wyliczamy predkosc katowa po zastosowaniu sterowania rozmytego
                    domega_fuzzy = (tau_fuzzy - params.get("b", 0.0) * omega_fuzzy - params.get("disturbance", 0.0)) / I # dw/dt = (tau - b*w - disturbance) / I
                    omega_fuzzy += domega_fuzzy * dt    
                    
                    # Calkowanie bledu bezwzglednego dla rozmytego
                    integral_error_abs_fuzzy += abs(setpoint - omega_fuzzy) * dt                                                                 # w = w(t) + dw/dt * dt

                    # Zapis danych do wykresu oraz statystyk rozmytych
                    omega_fuzzy_data.append(omega_fuzzy)
                    tau_fuzzy_data.append(tau_fuzzy)

                steady_state_error = setpoint - omega
                steady_state_error_fuzzy = setpoint - omega_fuzzy

                # Wyslanie danych symulacji w formie JSON do klienta
                try:
                    await websocket.send_json({
                        "type": "simulation_data",
                        "payload": {
                            "time": time_data,
                            "omega": omega_data,
                            "tau": tau_data,
                            "omega_fuzzy": omega_fuzzy_data,
                            "tau_fuzzy": tau_fuzzy_data,
                            "omega_set": setpoint,
                            "steady_state_error": steady_state_error,
                            "steady_state_error_fuzzy": steady_state_error_fuzzy,
                            "integral_error": integral_error_abs,
                            "integral_error_fuzzy": integral_error_abs_fuzzy
                        }
                    })
                except Exception as e:
                    print(f"Error sending data packet: {e}")


        except Exception as e:
            print(f"WebSocket error or disconnect: {e}")
            break

# To run the app, use the command:
# .\.venv\Scripts\Activate.ps1
# uvicorn main:app --reload
