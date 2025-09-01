# Archivos para tu repositorio Git

## .gitignore
```
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
.coverage
.pytest_cache/
*.log

# Configuración personal (no versionar)
printer_config.json
printer_config_android.json

# Build/Dist
build/
dist/
*.egg-info/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs específicos
label_client.log
*.log
```

## printer_config.json.example
```json
{
  "odoo_url": "https://tu-servidor-odoo.com",
  "printer_ip": "192.168.1.XXX",
  "printer_port": 9100,
  "auto_refresh": 10,
  "company_id": 1,
  "company_name": "Tu Empresa, C.A."
}
```

## printer_config_android.json.example
```json
{
  "odoo_url": "https://tu-servidor-odoo.com",
  "printer_ip": "192.168.1.XXX",
  "printer_port": 9100,
  "auto_refresh": 60,
  "company_id": 1,
  "company_name": "Tu Empresa, C.A.",
  "host": "0.0.0.0",
  "port": 8080,
  "debug": false
}
```

## android/setup_termux.sh
```bash
#!/bin/bash
echo "🤖 Configurando cliente de etiquetas para Android/Termux"

# Actualizar paquetes
pkg update && pkg upgrade -y

# Instalar dependencias del sistema
pkg install python python-pip git clang -y

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias Python
echo "Instalando dependencias Python..."
pip install Flask==2.3.3
pip install requests==2.31.0
pip install python-socketio==5.8.0
pip install python-engineio==4.7.1
pip install Flask-SocketIO==5.3.6

# Crear configuración desde ejemplo
if [ ! -f "printer_config.json" ]; then
    cp printer_config_android.json.example printer_config.json
    echo "📝 Creado printer_config.json - editarlo antes de usar"
fi

echo "✅ Instalación completa"
echo "📱 Editar printer_config.json y ejecutar: python web_label_client_android.py"
```

## android/run_android.sh
```bash
#!/bin/bash
cd ~/odoo_simple_label_print_client

# Verificar configuración
if [ ! -f "printer_config.json" ]; then
    echo "❌ Falta printer_config.json"
    echo "💡 Copiar desde printer_config_android.json.example"
    exit 1
fi

# Obtener IP local
IP=$(ip route get 1 | awk '{print $7}' | head -1)

echo "🤖 Iniciando Cliente de Etiquetas Android"
echo "📱 Local: http://localhost:8080"
echo "🌐 Red: http://$IP:8080"
echo ""

# Ejecutar
python web_label_client_android.py
```

## android/README_android.md
```markdown
# Cliente de Etiquetas - Android

## Instalación rápida en Termux

1. **Instalar Termux** desde F-Droid
2. **Clonar repo**:
   ```bash
   git clone https://github.com/tu-usuario/odoo_simple_label_print_client.git
   cd odoo_simple_label_print_client
   ```
3. **Ejecutar setup**:
   ```bash
   chmod +x android/setup_termux.sh
   ./android/setup_termux.sh
   ```
4. **Configurar**:
   ```bash
   nano printer_config.json
   # Editar URL, IP impresora, empresa
   ```
5. **Ejecutar**:
   ```bash
   python web_label_client_android.py
   ```

## Acceso
- Desde Android: `http://localhost:8080`
- Desde red: `http://IP_ANDROID:8080`

## Diferencias vs PC
- Puerto 8080 (no 5000)
- Auto-refresh 60s (ahorra batería)
- Threading async mode
- Timeouts optimizados
```

## requirements_android.txt
```
Flask==2.3.3
Flask-SocketIO==5.3.6
requests==2.31.0
python-socketio==5.8.0
python-engineio==4.7.1


