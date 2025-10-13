#!/bin/bash

# Piano LED Visualizer - Comprehensive Raspberry Pi Zero 2W Deployment Script
# For fresh Raspberry Pi Zero 2W setup
# Usage: ./deploy-to-pi-zero-2w.sh [--start STEP] [--start STEP]

set -e

# Configuration
PI_IP="192.168.1.225"
PI_USER="pi"
PROJECT_DIR="/home/pi/PianoLED-CoPilot"
REPO_URL="https://github.com/agwosdz/PianoLED-CoPilot.git"
BRANCH="main"

# Parse command line arguments
START_STEP=1
while [[ $# -gt 0 ]]; do
    case $1 in
        --start)
            START_STEP="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--start STEP]"
            echo "  --start STEP  Start deployment from step number (1-21, default: 1)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--start STEP]"
            exit 1
            ;;
    esac
done

echo "🚀 Comprehensive Deployment of Piano LED Visualizer to Raspberry Pi Zero 2W at $PI_IP"
echo "📅 $(date)"
echo "🎯 Starting from step $START_STEP"
echo ""

# Function to run commands on Pi via SSH
run_on_pi() {
    echo "🔧 Executing on Pi: $1"
    ssh -o StrictHostKeyChecking=no $PI_USER@$PI_IP "$1"
}

# Function to copy files to Pi
copy_to_pi() {
    echo "📤 Copying $1 to $2 on Pi"
    scp -o StrictHostKeyChecking=no -r "$1" $PI_USER@$PI_IP:"$2"
}

# Function to run a deployment step conditionally
run_step() {
    local step_num=$1
    local step_name=$2
    local step_function=$3
    
    if [ $step_num -ge $START_STEP ]; then
        echo ""
        echo "$step_name"
        $step_function
    else
        echo ""
        echo "⏭️  Skipping $step_name (starting from step $START_STEP)"
    fi
}

# Step function definitions
test_ssh_connection() {
    if ! ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $PI_USER@$PI_IP "echo 'SSH connection successful'"; then
        echo "❌ SSH connection failed. Please ensure:"
        echo "   - Raspberry Pi is powered on and connected to network"
        echo "   - SSH is enabled on the Pi"
        echo "   - SSH key authentication is configured"
        echo "   - IP address $PI_IP is correct"
        exit 1
    fi
}

system_prep() {
    run_on_pi "sudo apt update && sudo apt upgrade -y"
    run_on_pi "sudo apt install -y build-essential git curl wget unzip"
}

setup_locale() {
    run_on_pi "sudo raspi-config nonint do_change_locale en_US.UTF-8"
    run_on_pi "sudo raspi-config nonint do_change_timezone America/New_York"  # Adjust timezone as needed
}

install_python() {
    run_on_pi "sudo apt install -y python3 python3-pip python3-venv python3-dev python3-setuptools"
}

install_system_deps() {
    run_on_pi "sudo apt install -y libopenblas-dev libopenjp2-7-dev libtiff-dev libjpeg-dev libffi-dev zlib1g-dev"
    run_on_pi "sudo apt install -y i2c-tools spi-tools"  # For GPIO/I2C/SPI support
}

install_midi_deps() {
    run_on_pi "sudo apt install -y libasound2-dev libjack-jackd2-dev fluidsynth"
}

install_nodejs() {
    run_on_pi "curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -"
    run_on_pi "sudo apt install -y nodejs"
}

install_nginx() {
    run_on_pi "sudo apt install -y nginx"
    run_on_pi "sudo systemctl enable nginx"
}

configure_hardware() {
    # Enable SPI for LED control
    run_on_pi "sudo raspi-config nonint do_spi 0"
    # Enable I2C if needed for other peripherals
    run_on_pi "sudo raspi-config nonint do_i2c 0"
    # GPIO is enabled by default on Raspberry Pi OS
}

setup_gpio_permissions() {
    # Create necessary groups (ignore if they already exist)
    run_on_pi "sudo groupadd -g 123 spi 2>/dev/null || true"
    run_on_pi "sudo groupadd -g 124 gpio 2>/dev/null || true"
    run_on_pi "sudo groupadd -g 125 i2c 2>/dev/null || true"

    # Add pi user to the groups
    run_on_pi "sudo usermod -a -G spi pi"
    run_on_pi "sudo usermod -a -G gpio pi"
    run_on_pi "sudo usermod -a -G i2c pi"

    # Create udev rules for proper device permissions
    run_on_pi "sudo tee /etc/udev/rules.d/99-com.rules > /dev/null << 'EOF'
SUBSYSTEM==\"spidev\" , GROUP=\"spi\" , MODE=\"0660\"
KERNEL==\"i2c-0\"     , GROUP=\"i2c\" , MODE=\"0660\"
KERNEL==\"i2c-[1-9]*\", GROUP=\"i2c\" , MODE=\"0660\"
KERNEL==\"gpiomem\"   , GROUP=\"gpio\", MODE=\"0660\"
EOF"

    # Reload udev rules
    run_on_pi "sudo udevadm control --reload-rules && sudo udevadm trigger"
}

setup_project_dir() {
    run_on_pi "rm -rf $PROJECT_DIR"
    run_on_pi "git clone -b $BRANCH $REPO_URL $PROJECT_DIR"
    run_on_pi "cd $PROJECT_DIR && git submodule update --init --recursive"  # If any submodules
}

setup_python_env() {
    run_on_pi "cd $PROJECT_DIR/backend && python3 -m venv venv"
    run_on_pi "cd $PROJECT_DIR/backend && source venv/bin/activate && pip install --upgrade pip setuptools wheel"
    run_on_pi "cd $PROJECT_DIR/backend && source venv/bin/activate && pip install -r requirements.txt"
}

build_frontend() {
    # Skip npm install and build on Pi due to memory constraints
    # Frontend should be built locally and copied to the Pi
    echo "⚠️  Skipping frontend build on Pi (memory constrained)"
    echo "   Frontend files should be built locally and copied to $PROJECT_DIR/frontend/build"
}

create_env_config() {
    run_on_pi "cat > $PROJECT_DIR/.env << 'EOF'
# Flask Configuration
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0
FLASK_PORT=5001

# Hardware Configuration
BLINKA_USE_GPIOMEM=1
BLINKA_FORCEBOARD=RASPBERRY_PI_ZERO_2_W
BLINKA_FORCECHIP=BCM2XXX

# LED Configuration (adjust as needed)
LED_COUNT=88
LED_PIN=18
LED_FREQ_HZ=800000
LED_DMA=10
LED_BRIGHTNESS=255
LED_INVERT=False
LED_CHANNEL=0

# MIDI Configuration
MIDI_RTP_ENABLED=True
MIDI_USB_ENABLED=True

# Logging
LOG_LEVEL=INFO
EOF"
}

setup_systemd() {
    run_on_pi "sudo tee /etc/systemd/system/piano-led-visualizer.service > /dev/null << EOF
[Unit]
Description=Piano LED Visualizer Backend
After=network.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=$PROJECT_DIR/backend
Environment=PATH=$PROJECT_DIR/backend/venv/bin
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/backend/venv/bin/python start.py
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$PROJECT_DIR
ProtectHome=yes

[Install]
WantedBy=multi-user.target
EOF"
}

configure_nginx() {
    run_on_pi "sudo tee /etc/nginx/sites-available/piano-led-visualizer > /dev/null << 'EOF'
server {
    listen 80 default_server;
    server_name _;
    root $PROJECT_DIR/frontend/build;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/css application/javascript application/json;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;

    # Frontend static files
    location / {
        try_files \$uri \$uri/ /index.html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:5001/health;
        proxy_set_header Host \$host;
        access_log off;
    }

    # WebSocket proxy for Socket.IO
    location /socket.io/ {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_cache off;
    }
}
EOF"

    run_on_pi "sudo ln -sf /etc/nginx/sites-available/piano-led-visualizer /etc/nginx/sites-enabled/"
    run_on_pi "sudo rm -f /etc/nginx/sites-enabled/default"
}

setup_permissions() {
    run_on_pi "sudo chown -R pi:pi $PROJECT_DIR"
    run_on_pi "sudo chmod +x $PROJECT_DIR/backend/start.py"
}

configure_audio() {
    run_on_pi "sudo usermod -a -G audio pi"  # Add pi user to audio group
}

start_services() {
    run_on_pi "sudo systemctl daemon-reload"
    run_on_pi "sudo systemctl enable piano-led-visualizer.service"
    run_on_pi "sudo systemctl start piano-led-visualizer.service"
    run_on_pi "sudo systemctl restart nginx"
}

wait_for_services() {
    sleep 10
}

verify_deployment() {
    # Test backend health
    echo "Testing backend health..."
    if run_on_pi "curl -f --max-time 10 http://localhost:5001/health > /dev/null 2>&1"; then
        echo "✅ Backend health check: PASSED"
    else
        echo "❌ Backend health check: FAILED"
        echo "   Check logs: sudo journalctl -u piano-led-visualizer.service -f"
    fi

    # Test nginx
    echo "Testing nginx configuration..."
    if run_on_pi "curl -f --max-time 10 http://localhost > /dev/null 2>&1"; then
        echo "✅ Nginx serving frontend: PASSED"
    else
        echo "❌ Nginx serving frontend: FAILED"
        echo "   Check status: sudo systemctl status nginx"
    fi

    # Test full application
    echo "Testing full application..."
    if run_on_pi "curl -f --max-time 10 http://localhost/health > /dev/null 2>&1"; then
        echo "✅ Full application health check: PASSED"
    else
        echo "❌ Full application health check: FAILED"
    fi
}

run_step 1 "🔑 Step 1: Testing SSH connection..." "test_ssh_connection"
run_step 2 "📋 Step 2: System preparation and updates..." "system_prep"
run_step 3 "🌍 Step 3: Setting up locale and timezone..." "setup_locale"
run_step 4 "🐍 Step 4: Installing Python 3 and development tools..." "install_python"
run_step 5 "📦 Step 5: Installing system dependencies for hardware support..." "install_system_deps"
run_step 6 "🎵 Step 6: Installing MIDI and audio dependencies..." "install_midi_deps"
run_step 7 "⚡ Step 7: Installing Node.js 22.x..." "install_nodejs"
run_step 8 "🌐 Step 8: Installing and configuring nginx..." "install_nginx"
run_step 9 "🔧 Step 9: Configuring Raspberry Pi hardware interfaces..." "configure_hardware"
run_step 10 "🔒 Step 10: Setting up GPIO permissions for user access..." "setup_gpio_permissions"
run_step 11 "📁 Step 11: Setting up project directory..." "setup_project_dir"
run_step 12 "🐍 Step 12: Setting up Python virtual environment and dependencies..." "setup_python_env"
run_step 13 "⚛️ Step 13: Building frontend..." "build_frontend"
run_step 14 "⚙️ Step 14: Creating environment configuration..." "create_env_config"
run_step 15 "🔧 Step 15: Setting up systemd service..." "setup_systemd"
run_step 16 "🌐 Step 16: Configuring nginx reverse proxy..." "configure_nginx"
run_step 17 "🔒 Step 17: Setting up proper permissions..." "setup_permissions"
run_step 18 "🎛️ Step 18: Configuring audio (optional, for MIDI playback)..." "configure_audio"
run_step 19 "🚀 Step 19: Starting and enabling services..." "start_services"
run_step 20 "⏳ Step 20: Waiting for services to start..." "wait_for_services"
run_step 21 "✅ Step 21: Verifying deployment..." "verify_deployment"

echo ""
echo "🎉 Deployment Complete!"
echo "📱 Access your Piano LED Visualizer at: http://$PI_IP"
echo "🔍 Health check endpoint: http://$PI_IP/health"
echo ""
echo "📊 Service Management Commands:"
echo "  View backend logs: ssh $PI_USER@$PI_IP 'sudo journalctl -u piano-led-visualizer.service -f'"
echo "  Restart backend:   ssh $PI_USER@$PI_IP 'sudo systemctl restart piano-led-visualizer.service'"
echo "  Restart nginx:     ssh $PI_USER@$PI_IP 'sudo systemctl restart nginx'"
echo "  Check status:      ssh $PI_USER@$PI_IP 'sudo systemctl status piano-led-visualizer.service'"
echo ""
echo "🔧 Troubleshooting:"
echo "  If LEDs don't work: Check SPI is enabled (raspi-config) and LED configuration in .env"
echo "  If MIDI doesn't work: Ensure USB MIDI device is connected or RTP MIDI is configured"
echo "  If web interface doesn't load: Check nginx logs with 'sudo journalctl -u nginx -f'"
echo ""
echo "⚠️  Post-deployment tasks:"
echo "  1. Connect your MIDI keyboard/piano"
echo "  2. Connect LED strip to GPIO pin 18 (or configured pin)"
echo "  3. Adjust LED_COUNT in .env to match your setup"
echo "  4. Test the web interface and LED responsiveness"
echo "  5. Reboot the Pi for GPIO permissions to take full effect: sudo reboot"
echo ""
echo "📚 For more information, see the project README and backend/tools/ documentation."