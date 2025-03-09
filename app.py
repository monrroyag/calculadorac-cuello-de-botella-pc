import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Ruta del archivo JSON con los datos de las GPUs y CPUs
JSON_FILE = 'hardware_data.json'

# Función para cargar datos del archivo JSON
def load_json_data():
    with open(JSON_FILE, 'r') as file:
        data = json.load(file)
    return data

# Función para obtener los detalles de la GPU seleccionada
def get_gpu_details(gpu_name, gpu_data):
    gpu_details = next((gpu for gpu in gpu_data if gpu['name'] == gpu_name), None)
    return gpu_details

# Función para obtener los detalles de la CPU seleccionada
def get_cpu_details(cpu_name, cpu_data):
    cpu_details = next((cpu for cpu in cpu_data if cpu['name'] == cpu_name), None)
    return cpu_details

# Función para convertir frecuencias de tipo rango a promedio
def convert_to_float(frequency_str):
    try:
        if 'to' in frequency_str:  # Si el valor es un rango
            # Dividir el rango y tomar el valor base
            low, high = frequency_str.split(' to ')
            return float(low)  # Usamos solo el valor base
        else:
            # Si no es un rango, convertir directamente
            return float(frequency_str.replace(' GHz', '').replace(' MHz', '').strip())
    except ValueError:
        return 0.0  # Manejar errores si la conversión falla

# Función para convertir a entero, manejando casos de valores no numéricos
def convert_to_int(value):
    try:
        return int(value)
    except ValueError:
        return 0  # Valor predeterminado si no se puede convertir

# Función para manejar los núcleos de la CPU, para cuando no es un número
def handle_cores(value):
    known_cpu_cores = {
        'Vermeer': 8,
        'Cezanne': 6,
    }
    try:
        return int(value.split('/')[0]) if '/' in value else int(value)
    except ValueError:
        return known_cpu_cores.get(value, 0)

# Función para obtener el TDP, manejando el caso de clave faltante
def get_tdp(cpu_details):
    return float(cpu_details['tdp'].replace('W', '').strip()) if 'tdp' in cpu_details and cpu_details['tdp'] else 0

# Función para realizar el cálculo detallado del cuello de botella
def calculate_bottleneck(cpu_details, gpu_details):
    cpu_base_clock = convert_to_float(cpu_details['base_clock'])  # Usar solo la frecuencia base
    gpu_base_clock = float(gpu_details['base_clock'].replace(' MHz', '')) / 1000  # Convertir a GHz
    cpu_cores = handle_cores(cpu_details['cores'])  # Manejar núcleos no numéricos
    gpu_cores = convert_to_int(gpu_details['cores'])
    
    cpu_tdp = get_tdp(cpu_details)
    gpu_tdp = float(gpu_details['power_consumption'].replace('W', '').strip()) if 'power_consumption' in gpu_details else 0

    # Comparar las frecuencias y núcleos para el cuello de botella
    bottleneck_message = f"Frecuencia de la CPU: {cpu_base_clock} GHz | Frecuencia de la GPU: {gpu_base_clock} GHz\n"
    
    # Analizar frecuencia
    if cpu_base_clock < gpu_base_clock:
        bottleneck_message += "Posible cuello de botella: La CPU podría limitar el rendimiento de la GPU debido a la frecuencia.\n"
    elif cpu_base_clock > gpu_base_clock:
        bottleneck_message += "La frecuencia de la CPU es suficiente para la GPU.\n"
    
    # Comparar núcleos
    if cpu_cores < gpu_cores:
        bottleneck_message += "Posible cuello de botella: La CPU tiene menos núcleos, lo que puede limitar el rendimiento de la GPU.\n"
    elif cpu_cores >= gpu_cores:
        bottleneck_message += "La CPU tiene suficientes núcleos para manejar la carga.\n"
    
    # Analizar TDP
    if cpu_tdp < gpu_tdp:
        bottleneck_message += "Posible cuello de botella: La CPU tiene un TDP más bajo, lo que puede indicar un rendimiento limitado en cargas pesadas.\n"
    elif cpu_tdp >= gpu_tdp:
        bottleneck_message += "La CPU tiene un TDP adecuado para manejar la carga.\n"

    # Determinar si hay un cuello de botella
    if cpu_base_clock < gpu_base_clock or cpu_cores < gpu_cores:
        bottleneck_message += "La CPU está probablemente limitando el rendimiento de la GPU en términos de frecuencia o núcleos.\n"
    else:
        bottleneck_message += "No parece haber un cuello de botella aparente entre la CPU y la GPU.\n"
    
    return bottleneck_message

@app.route('/', methods=['GET', 'POST'])
def index():
    data = load_json_data()  # Cargar los datos del archivo JSON
    gpu_data = data.get('gpu_data', [])
    cpu_data = data.get('cpu_data', [])

    bottleneck_message = ""
    gpu_details = {}
    cpu_details = {}

    if request.method == 'POST':
        gpu_name = request.form['gpu_name']
        cpu_name = request.form['cpu_name']

        # Obtener los detalles de la GPU y CPU seleccionados
        gpu_details = get_gpu_details(gpu_name, gpu_data)
        cpu_details = get_cpu_details(cpu_name, cpu_data)

        # Realizar el análisis detallado de cuello de botella usando los datos
        if gpu_details and cpu_details:
            bottleneck_message = calculate_bottleneck(cpu_details, gpu_details)

    return render_template('index.html', gpu_data=gpu_data, cpu_data=cpu_data, bottleneck_message=bottleneck_message, gpu_details=gpu_details, cpu_details=cpu_details)

@app.route('/download_data', methods=['GET'])
def download_data():
    data = load_json_data()  # Cargar los datos desde el JSON
    return jsonify(data)  # Enviar los datos en formato JSON

if __name__ == '__main__':
    app.run(debug=True)
