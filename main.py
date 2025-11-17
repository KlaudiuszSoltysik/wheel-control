import json
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
static = Jinja2Templates(directory="static")

@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    return static.TemplateResponse("index.html", {"request": request})

# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#
#     while True:
#         try:
#             msg = await websocket.receive_text()
#             data = json.loads(msg)
#
#             if data.get('type') == 'start_simulation':
#
#                 params = data.get('payload', {})
#
#                 m = params.get("mass", 1.0)
#                 r = params.get("radius", 0.5)
#                 I = 0.5 * m * r**2
#
#                 setpoint = params.get("omega_set", 0.0)
#
#                 time_data = []
#                 omega_data = []
#                 tau_data = []
#
#                 omega = 0.0
#                 integral = 0.0
#                 prev_error = 0.0
#                 dt = 0.001
#                 time = 0.0
#                 integral_sum_abs = 0
#
#                 time_data.append(time)
#                 omega_data.append(omega)
#                 tau_data.append(0)
#
#                 for _ in range(60000):
#                     error = setpoint - omega
#                     integral += error * dt
#                     integral_sum_abs += abs(integral)
#                     derivative = (error - prev_error) / dt
#                     prev_error = error
#
#                     tau_pid = (params.get("Kp", 0.0) * error +
#                                params.get("Ki", 0.0) * integral +
#                                params.get("Kd", 0.0) * derivative)
#
#                     max_tau = params.get("maxMoment", 0.5)
#                     tau_clamped = max(-max_tau, min(max_tau, tau_pid))
#
#                     domega = (tau_clamped - params.get("b", 0.0) * omega - params.get("disturbance", 0.0)) / I
#                     omega += domega * dt
#                     time += dt
#
#                     time_data.append(round(time, 3))
#                     omega_data.append(omega)
#                     tau_data.append(tau_clamped)
#
#                 tolerance = max(0.02 * abs(setpoint), 0.02)
#                 upper_band = setpoint + tolerance
#                 lower_band = setpoint - tolerance
#
#                 settled_index = -1
#                 for i in range(len(omega_data) - 1, -1, -1):
#                     if not (lower_band <= omega_data[i] <= upper_band):
#                         settled_index = i + 1
#                         break
#
#                 if settled_index == -1:
#                     settling_time = time_data[0]
#                 elif settled_index >= len(time_data):
#                     settling_time = -1
#                 else:
#                     settling_time = time_data[settled_index]
#
#                 steady_state_error = setpoint - omega_data[-1]
#                 integral_error = integral_sum_abs
#                 integral_tau_abs = sum(abs(t) for t in tau_data) * dt
#
#                 try:
#                     await websocket.send_json({
#                         "type": "simulation_data",
#                         "payload": {
#                             "time": time_data,
#                             "omega": omega_data,
#                             "tau": tau_data,
#                             "omega_set": setpoint,
#                             "stats": {
#                                 "settling_time": settling_time,
#                                 "steady_state_error": steady_state_error,
#                                 "integral_error": integral_error,
#                                 "integral_tau_abs": integral_tau_abs
#                             }
#                         }
#                     })
#                 except Exception as e:
#                     print(f"Error sending data packet: {e}")
#
#
#         except Exception as e:
#             print(f"WebSocket error or disconnect: {e}")
#             break

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        try:
            msg = await websocket.receive_text()
            data = json.loads(msg)

            if data.get('type') == 'start_simulation':
                params = data.get('payload', {})

                m = params.get("mass", 1.0)
                r = params.get("radius", 0.5)
                I = 0.5 * m * r**2

                setpoint = params.get("omega_set", 0.0)

                time_data = []
                omega_data = []
                tau_data = []

                omega = 0.0
                integral = 0.0
                prev_error = 0.0
                dt = 0.001
                time = 0.0
                integral_error_abs = 0.0

                time_data.append(time)
                omega_data.append(omega)
                tau_data.append(0)

                tolerance = max(0.01 * abs(setpoint), 0.01)
                upper_band = setpoint + tolerance
                lower_band = setpoint - tolerance

                time_inside_band = 0.0
                settling_time_required = 10.0
                settling_time = -1

                max_iterations = 120000

                for _ in range(max_iterations):
                    error = setpoint - omega
                    integral += error * dt
                    integral_error_abs += abs(error) * dt
                    derivative = (error - prev_error) / dt
                    prev_error = error

                    tau_pid = (params.get("Kp", 0.0) * error +
                               params.get("Ki", 0.0) * integral +
                               params.get("Kd", 0.0) * derivative)

                    max_tau = params.get("maxMoment", 0.5)
                    tau_clamped = max(-max_tau, min(max_tau, tau_pid))

                    domega = (tau_clamped - params.get("b", 0.0) * omega - params.get("disturbance", 0.0)) / I
                    omega += domega * dt
                    time += dt

                    time_data.append(round(time, 3))
                    omega_data.append(omega)
                    tau_data.append(tau_clamped)

                    if lower_band <= omega <= upper_band:
                        time_inside_band += dt
                        if time_inside_band >= settling_time_required:
                            settling_time = time - time_inside_band
                            break
                    else:
                        time_inside_band = 0.0

                steady_state_error = setpoint - omega_data[-1]
                integral_error = integral_error_abs
                integral_tau_abs = sum(abs(t) for t in tau_data) * dt

                try:
                    await websocket.send_json({
                        "type": "simulation_data",
                        "payload": {
                            "time": time_data,
                            "omega": omega_data,
                            "tau": tau_data,
                            "omega_set": setpoint,
                            "stats": {
                                "settling_time": settling_time,
                                "steady_state_error": steady_state_error,
                                "integral_error": integral_error,
                                "integral_tau_abs": integral_tau_abs
                            }
                        }
                    })
                except Exception as e:
                    print(f"Error sending data packet: {e}")


        except Exception as e:
            print(f"WebSocket error or disconnect: {e}")
            break

# uvicorn main:app --reload
