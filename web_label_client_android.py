#!/usr/bin/env python3
"""
Cliente web para Android/Termux - Optimizado para móviles
"""

import json
import socket
import requests
import time
import os
from flask import Flask, render_template, jsonify, request as flask_request
from flask_socketio import SocketIO, emit
import logging

# Configurar logging para Android
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'label_print_android'
# IMPORTANTE: usar threading en Android, no eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Variables globales
config = {}
zpl_templates = {}

def get_android_ip():
    """Obtener IP local de Android"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except:
        return "localhost"

def load_config():
    """Cargar configuración - Android compatible"""
    global config, zpl_templates
    
    # Buscar configuración específica para Android
    config_files = ['printer_config_android.json']
    
    for config_file in config_files:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"Configuración cargada desde {config_file}")
                break
        except FileNotFoundError:
            continue
    try:
        with open('zpl_templates.json', 'r', encoding='utf-8') as f:
            zpl_templates = json.load(f)
    except FileNotFoundError:
        logger.error("No existe zpl_templates.json - crear archivo")
        zpl_templates = {}

def save_config():
    """Guardar configuración en Android"""
    config_file = 'printer_config_android.json'
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Configuración guardada en {config_file}")
    except Exception as e:
        logger.error(f"Error guardando configuración: {e}")

def imprimir_etiqueta_zpl(zpl_code):
    """Envía ZPL a impresora - timeout reducido para Android"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)  # Timeout reducido
        sock.connect((config['printer_ip'], config['printer_port']))
        sock.send(zpl_code.encode('utf-8'))
        sock.close()
        return True, "Enviado correctamente"
    except Exception as e:
        return False, str(e)

def get_pending_jobs():
    """Obtiene trabajos pendientes - timeout optimizado"""
    try:
        url = f"{config['odoo_url']}/api/label_print/jobs"
        
        payload = {}
        if config.get('company_id'):
            payload['company_id'] = config['company_id']
            
        response = requests.post(url, json=payload, timeout=10)  # Timeout reducido
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                jobs = data.get('jobs', [])
                logger.info(f"Obtenidos {len(jobs)} trabajos")
                return jobs
        return []
    except Exception as e:
        logger.error(f"Error obteniendo trabajos: {e}")
        return []

def update_job_status(job_id, status, error_message=None):
    """Actualiza estado en Odoo - timeout optimizado"""
    try:
        url = f"{config['odoo_url']}/api/label_print/update_job"
        payload = {"job_id": job_id, "status": status}
        if error_message:
            payload["error_message"] = error_message
            
        response = requests.post(url, json=payload, timeout=8)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error actualizando: {e}")
        return False

def generate_zpl(job_data, template_name="standard"):
    """Genera ZPL desde template"""
    if not zpl_templates:
        logger.error("No hay templates ZPL disponibles")
        return []
        
    template = zpl_templates.get(template_name)
    if not template:
        logger.error(f"Template '{template_name}' no encontrado")
        return []
    
    # Preparar datos para template
    data = {
        'product_name': job_data.get('product_name', 'PRODUCTO')[:20],
        'default_code': job_data.get('default_code', ''),
        'barcode': job_data.get('barcode', ''),
        'price': float(job_data.get('calculated_price', job_data.get('list_price', 0))),
        'currency_symbol': job_data.get('currency_symbol', '$'), 
    }
    
    quantity = int(job_data.get('custom_quantity', 1))
    zpl_commands = []
    
    for i in range(quantity):
        try:
            zpl = template['template'].format(**data)
            zpl_commands.append(zpl)
        except KeyError as e:
            logger.error(f"Error en template: campo {e} no encontrado")
            return []
    
    return zpl_commands

# Rutas web
@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/jobs')
def api_jobs():
    """API local para obtener trabajos"""
    jobs = get_pending_jobs()
    return jsonify({
        'success': True,
        'jobs': jobs,
        'count': len(jobs)
    })

@app.route('/api/config')
def api_config():
    """Obtener configuración"""
    return jsonify({
        'config': {
            'odoo_url': config.get('odoo_url', ''),
            'auto_refresh': config.get('auto_refresh', 60)
        },
        'templates': {name: data['name'] for name, data in zpl_templates.items()}
    })

@app.route('/api/config', methods=['POST'])
def api_save_config():
    """Guardar configuración"""
    global config
    data = flask_request.json
    
    if 'odoo_url' in data:
        config['odoo_url'] = data['odoo_url']
    if 'auto_refresh' in data:
        config['auto_refresh'] = int(data['auto_refresh'])
    
    save_config()
    return jsonify({'success': True})

# WebSocket events
@socketio.on('print_job')
def handle_print_job(data):
    """Manejar impresión de trabajo"""
    job_id = data.get('job_id')
    template = data.get('template', 'standard')
    
    jobs = get_pending_jobs()
    job = next((j for j in jobs if j['id'] == job_id), None)
    
    if not job:
        emit('print_result', {
            'success': False, 
            'message': 'Trabajo no encontrado'
        })
        return
    
    try:
        emit('print_status', {'message': f"Generando ZPL para {job['product_name']}"})
        
        zpl_commands = generate_zpl(job, template)
        if not zpl_commands:
            emit('print_result', {
                'success': False,
                'message': 'Error generando ZPL'
            })
            return
        
        emit('print_status', {'message': f"Imprimiendo {len(zpl_commands)} etiquetas"})
        
        for i, zpl in enumerate(zpl_commands):
            success, message = imprimir_etiqueta_zpl(zpl)
            
            if not success:
                update_job_status(job_id, 'error', message)
                emit('print_result', {
                    'success': False,
                    'message': f'Error: {message}'
                })
                return
            
            emit('print_status', {'message': f"Etiqueta {i+1}/{len(zpl_commands)} enviada"})
            time.sleep(0.1)  # Pausa reducida para Android
        
        update_job_status(job_id, 'done')
        emit('print_result', {
            'success': True,
            'message': f'✅ {len(zpl_commands)} etiquetas impresas'
        })
        
    except Exception as e:
        logger.error(f"Error imprimiendo: {e}")
        update_job_status(job_id, 'error', str(e))
        emit('print_result', {
            'success': False,
            'message': str(e)
        })

@socketio.on('print_all')
def handle_print_all(data):
    """Imprimir todos los trabajos"""
    template = data.get('template', 'standard')
    jobs = get_pending_jobs()
    
    if not jobs:
        emit('print_result', {
            'success': False,
            'message': 'No hay trabajos pendientes'
        })
        return
    
    emit('print_status', {'message': f"Procesando {len(jobs)} trabajos"})
    
    success_count = 0
    for job in jobs:
        try:
            zpl_commands = generate_zpl(job, template)
            
            for zpl in zpl_commands:
                success, message = imprimir_etiqueta_zpl(zpl)
                if not success:
                    update_job_status(job['id'], 'error', message)
                    continue
            
            update_job_status(job['id'], 'done')
            success_count += 1
            emit('print_status', {'message': f"✅ {job['product_name']}"})
            
        except Exception as e:
            update_job_status(job['id'], 'error', str(e))
    
    emit('print_result', {
        'success': True,
        'message': f'Procesados {success_count}/{len(jobs)} trabajos'
    })

if __name__ == '__main__':
    load_config()
    
    host = config.get('host', '0.0.0.0')
    port = config.get('port', 8080)
    debug = config.get('debug', False)
    
    android_ip = get_android_ip()
    
    print(f"🤖 Cliente de Etiquetas - Android")
    print(f"📱 Local: http://localhost:{port}")
    print(f"🌐 Red: http://{android_ip}:{port}")
    print(f"🖨️ Impresora: {config.get('printer_ip', 'NO CONFIGURADA')}")
    print(f"🏢 Empresa: {config.get('company_name', 'N/A')}")
    
    try:
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
    except Exception as e:
        logger.error(f"Error iniciando servidor: {e}")
        print("💡 Intenta cambiar el puerto en printer_config.json")
