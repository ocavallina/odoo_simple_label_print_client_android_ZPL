#!/bin/bash

case "$1" in
    start)
        nohup ~/.termux/boot/label_client &
        echo "✅ Servicio iniciado"
        ;;
    stop)
        pkill -f "web_label_client_android.py"
        pkill -f "label_client"
        echo "✅ Servicio detenido"
        ;;
    logs)
        tail -20 ~/label_service.log
        ;;
    *)
        echo "Uso: $0 {start|stop|logs}"
        ;;
esac
