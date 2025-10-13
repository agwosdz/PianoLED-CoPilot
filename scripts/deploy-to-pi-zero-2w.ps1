# Piano LED Visualizer - Comprehensive Raspberry Pi Zero 2W Deployment Script
# For fresh Raspberry Pi Zero 2W setup
# PowerShell version
# Usage: .\deploy-to-pi-zero-2w.ps1 [-Start STEP]

param(
    [string]$PiIp = "192.168.1.225",
    [string]$PiUser = "pi",
    [int]$Start = 1
)

# Configuration
$PROJECT_DIR = "/home/pi/PianoLED-CoPilot"
$REPO_URL = "git@github.com:agwosdz/PianoLED-CoPilot.git"
$BRANCH = "main"

Write-Host "🚀 Comprehensive Deployment of Piano LED Visualizer to Raspberry Pi Zero 2W at $PiIp" -ForegroundColor Green
Write-Host "📅 $(Get-Date)" -ForegroundColor Green
Write-Host "🎯 Starting from step $Start" -ForegroundColor Green
Write-Host ""

# Function to run commands on Pi via SSH
function Invoke-OnPi {
    param([string]$Command)
    Write-Host "🔧 Executing on Pi: $Command" -ForegroundColor Yellow
    try {
        $result = ssh -o StrictHostKeyChecking=no $PiUser@$PiIp $Command 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code $LASTEXITCODE"
        }
        return $result
    }
    catch {
        Write-Error "SSH command failed: $_"
        exit 1
    }
}

# Function to copy files to Pi
function Copy-ToPi {
    param([string]$Source, [string]$Destination)
    Write-Host "📤 Copying $Source to $Destination on Pi" -ForegroundColor Cyan
    try {
        scp -o StrictHostKeyChecking=no -r $Source $PiUser@$PiIp`:$Destination
        if ($LASTEXITCODE -ne 0) {
            throw "SCP failed with exit code $LASTEXITCODE"
        }
    }
    catch {
        Write-Error "SCP failed: $_"
        exit 1
    }
}

# Function to run a deployment step conditionally
function Invoke-Step {
    param([int]$StepNum, [string]$StepName, [scriptblock]$StepFunction)

    if ($StepNum -ge $Start) {
        Write-Host ""
        Write-Host $StepName -ForegroundColor Blue
        & $StepFunction
    }
    else {
        Write-Host ""
        Write-Host "⏭️  Skipping $StepName (starting from step $Start)" -ForegroundColor Gray
    }
}

# Step function definitions
function Test-SshConnection {
    try {
        $testResult = ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $PiUser@$PiIp "echo 'SSH connection successful'" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Error "❌ SSH connection failed. Please ensure:"
            Write-Error "   - Raspberry Pi is powered on and connected to network"
            Write-Error "   - SSH is enabled on the Pi"
            Write-Error "   - SSH key authentication is configured"
            Write-Error "   - IP address $PiIp is correct"
            exit 1
        }
    }
    catch {
        Write-Error "SSH test failed: $_"
        exit 1
    }
}

function Invoke-SystemPrep {
    Invoke-OnPi "sudo apt update && sudo apt upgrade -y"
    Invoke-OnPi "sudo apt install -y build-essential git curl wget unzip"
}

function Set-Locale {
    Invoke-OnPi "sudo raspi-config nonint do_change_locale en_US.UTF-8"
    Invoke-OnPi "sudo raspi-config nonint do_change_timezone America/New_York"  # Adjust timezone as needed
}

function Install-Python {
    Invoke-OnPi "sudo apt install -y python3 python3-pip python3-venv python3-dev python3-setuptools"
}

function Install-SystemDeps {
    Invoke-OnPi "sudo apt install -y libopenblas-dev libopenjp2-7-dev libtiff-dev libjpeg-dev libffi-dev zlib1g-dev"
    Invoke-OnPi "sudo apt install -y i2c-tools spi-tools"  # For GPIO/I2C/SPI support
}

function Install-MidiDeps {
    Invoke-OnPi "sudo apt install -y libasound2-dev libjack-jackd2-dev fluidsynth"
}

function Install-NodeJs {
    Invoke-OnPi "curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -"
    Invoke-OnPi "sudo apt install -y nodejs"
}

function Install-Nginx {
    Invoke-OnPi "sudo apt install -y nginx"
    Invoke-OnPi "sudo systemctl enable nginx"
}

function Set-HardwareConfig {
    # Enable SPI for LED control
    Invoke-OnPi "sudo raspi-config nonint do_spi 0"
    # Enable I2C if needed for other peripherals
    Invoke-OnPi "sudo raspi-config nonint do_i2c 0"
    # GPIO is enabled by default on Raspberry Pi OS
}

function Set-GpioPermissions {
    # Create necessary groups (ignore if they already exist)
    Invoke-OnPi "sudo groupadd -g 123 spi 2>/dev/null || true"
    Invoke-OnPi "sudo groupadd -g 124 gpio 2>/dev/null || true"
    Invoke-OnPi "sudo groupadd -g 125 i2c 2>/dev/null || true"

    # Add pi user to the groups
    Invoke-OnPi "sudo usermod -a -G spi pi"
    Invoke-OnPi "sudo usermod -a -G gpio pi"
    Invoke-OnPi "sudo usermod -a -G i2c pi"

    # Create udev rules for proper device permissions
    $udevRules = @"
SUBSYSTEM=="spidev" , GROUP="spi" , MODE="0660"
KERNEL=="i2c-0"     , GROUP="i2c" , MODE="0660"
KERNEL=="i2c-[1-9]*", GROUP="i2c" , MODE="0660"
KERNEL=="gpiomem"   , GROUP="gpio", MODE="0660"
"@

    Invoke-OnPi "sudo tee /etc/udev/rules.d/99-com.rules > /dev/null << 'EOF'
$udevRules
EOF"

    # Reload udev rules
    Invoke-OnPi "sudo udevadm control --reload-rules && sudo udevadm trigger"
}

function Set-ProjectDir {
    Invoke-OnPi "rm -rf $PROJECT_DIR"
    Invoke-OnPi "git clone -b $BRANCH $REPO_URL $PROJECT_DIR"
    Invoke-OnPi "cd $PROJECT_DIR && git submodule update --init --recursive"  # If any submodules
}

function Set-PythonEnv {
    Invoke-OnPi "cd $PROJECT_DIR/backend && python3 -m venv venv"
    Invoke-OnPi "cd $PROJECT_DIR/backend && source venv/bin/activate && pip install --upgrade pip setuptools wheel"
    Invoke-OnPi "cd $PROJECT_DIR/backend && source venv/bin/activate && pip install -r requirements.txt"
}

function Build-Frontend {
    # Skip npm install and build on Pi due to memory constraints
    # Frontend should be built locally and copied to the Pi
    Write-Host "⚠️  Skipping frontend build on Pi (memory constrained)" -ForegroundColor Yellow
    Write-Host "   Frontend files should be built locally and copied to $PROJECT_DIR/frontend/build" -ForegroundColor White
}

function New-EnvConfig {
    $envConfig = @"
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
"@

    Invoke-OnPi "cat > $PROJECT_DIR/.env << 'EOF'
$envConfig
EOF"
}

function Set-SystemdService {
    $serviceConfig = @"
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
"@

    Invoke-OnPi "sudo tee /etc/systemd/system/piano-led-visualizer.service > /dev/null << EOF
$serviceConfig
EOF"
}

function Set-NginxConfig {
    $nginxConfig = @'
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
        try_files $uri $uri/ /index.html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:5001/health;
        proxy_set_header Host $host;
        access_log off;
    }

    # WebSocket proxy for Socket.IO
    location /socket.io/ {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_cache off;
    }
}
'@

    Invoke-OnPi "sudo tee /etc/nginx/sites-available/piano-led-visualizer > /dev/null << 'EOF'
$nginxConfig
EOF"

    Invoke-OnPi "sudo ln -sf /etc/nginx/sites-available/piano-led-visualizer /etc/nginx/sites-enabled/"
    Invoke-OnPi "sudo rm -f /etc/nginx/sites-enabled/default"
}

function Set-Permissions {
    Invoke-OnPi "sudo chown -R pi:pi $PROJECT_DIR"
    Invoke-OnPi "sudo chmod +x $PROJECT_DIR/backend/start.py"
}

function Set-AudioConfig {
    Invoke-OnPi "sudo usermod -a -G audio pi"  # Add pi user to audio group
}

function Start-Services {
    Invoke-OnPi "sudo systemctl daemon-reload"
    Invoke-OnPi "sudo systemctl enable piano-led-visualizer.service"
    Invoke-OnPi "sudo systemctl start piano-led-visualizer.service"
    Invoke-OnPi "sudo systemctl restart nginx"
}

function Wait-ForServices {
    Start-Sleep -Seconds 10
}

function Test-Deployment {
    # Test backend health
    Write-Host "Testing backend health..." -ForegroundColor Yellow
    try {
        Invoke-OnPi "curl -f --max-time 10 http://localhost:5001/health > /dev/null 2>&1"
        Write-Host "✅ Backend health check: PASSED" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Backend health check: FAILED" -ForegroundColor Red
        Write-Host "   Check logs: sudo journalctl -u piano-led-visualizer.service -f" -ForegroundColor Red
    }

    # Test nginx
    Write-Host "Testing nginx configuration..." -ForegroundColor Yellow
    try {
        Invoke-OnPi "curl -f --max-time 10 http://localhost > /dev/null 2>&1"
        Write-Host "✅ Nginx serving frontend: PASSED" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Nginx serving frontend: FAILED" -ForegroundColor Red
        Write-Host "   Check status: sudo systemctl status nginx" -ForegroundColor Red
    }

    # Test full application
    Write-Host "Testing full application..." -ForegroundColor Yellow
    try {
        Invoke-OnPi "curl -f --max-time 10 http://localhost/health > /dev/null 2>&1"
        Write-Host "✅ Full application health check: PASSED" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Full application health check: FAILED" -ForegroundColor Red
    }
}

# Execute deployment steps
Invoke-Step 1 "🔑 Step 1: Testing SSH connection..." ${function:Test-SshConnection}
Invoke-Step 2 "📋 Step 2: System preparation and updates..." ${function:Invoke-SystemPrep}
Invoke-Step 3 "🌍 Step 3: Setting up locale and timezone..." ${function:Set-Locale}
Invoke-Step 4 "🐍 Step 4: Installing Python 3 and development tools..." ${function:Install-Python}
Invoke-Step 5 "📦 Step 5: Installing system dependencies for hardware support..." ${function:Install-SystemDeps}
Invoke-Step 6 "🎵 Step 6: Installing MIDI and audio dependencies..." ${function:Install-MidiDeps}
Invoke-Step 7 "⚡ Step 7: Installing Node.js 22.x..." ${function:Install-NodeJs}
Invoke-Step 8 "🌐 Step 8: Installing and configuring nginx..." ${function:Install-Nginx}
Invoke-Step 9 "🔧 Step 9: Configuring Raspberry Pi hardware interfaces..." ${function:Set-HardwareConfig}
Invoke-Step 10 "🔒 Step 10: Setting up GPIO permissions for user access..." ${function:Set-GpioPermissions}
Invoke-Step 11 "📁 Step 11: Setting up project directory..." ${function:Set-ProjectDir}
Invoke-Step 12 "🐍 Step 12: Setting up Python virtual environment and dependencies..." ${function:Set-PythonEnv}
Invoke-Step 13 "⚛️ Step 13: Building frontend..." ${function:Build-Frontend}
Invoke-Step 14 "⚙️ Step 14: Creating environment configuration..." ${function:New-EnvConfig}
Invoke-Step 15 "🔧 Step 15: Setting up systemd service..." ${function:Set-SystemdService}
Invoke-Step 16 "🌐 Step 16: Configuring nginx reverse proxy..." ${function:Set-NginxConfig}
Invoke-Step 17 "🔒 Step 17: Setting up proper permissions..." ${function:Set-Permissions}
Invoke-Step 18 "🎛️ Step 18: Configuring audio (optional, for MIDI playback)..." ${function:Set-AudioConfig}
Invoke-Step 19 "🚀 Step 19: Starting and enabling services..." ${function:Start-Services}
Invoke-Step 20 "⏳ Step 20: Waiting for services to start..." ${function:Wait-ForServices}
Invoke-Step 21 "✅ Step 21: Verifying deployment..." ${function:Test-Deployment}

Write-Host ""
Write-Host "🎉 Deployment Complete!" -ForegroundColor Green
Write-Host "📱 Access your Piano LED Visualizer at: http://$PiIp" -ForegroundColor Cyan
Write-Host "🔍 Health check endpoint: http://$PiIp/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Service Management Commands:" -ForegroundColor Magenta
Write-Host "  View backend logs: ssh $PiUser@$PiIp 'sudo journalctl -u piano-led-visualizer.service -f'" -ForegroundColor White
Write-Host "  Restart backend:   ssh $PiUser@$PiIp 'sudo systemctl restart piano-led-visualizer.service'" -ForegroundColor White
Write-Host "  Restart nginx:     ssh $PiUser@$PiIp 'sudo systemctl restart nginx'" -ForegroundColor White
Write-Host "  Check status:      ssh $PiUser@$PiIp 'sudo systemctl status piano-led-visualizer.service'" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Troubleshooting:" -ForegroundColor Yellow
Write-Host "  If LEDs don't work: Check SPI is enabled (raspi-config) and LED configuration in .env" -ForegroundColor White
Write-Host "  If MIDI doesn't work: Ensure USB MIDI device is connected or RTP MIDI is configured" -ForegroundColor White
Write-Host "  If web interface doesn't load: Check nginx logs with 'sudo journalctl -u nginx -f'" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  Post-deployment tasks:" -ForegroundColor Yellow
Write-Host "  1. Connect your MIDI keyboard/piano" -ForegroundColor White
Write-Host "  2. Connect LED strip to GPIO pin 18 (or configured pin)" -ForegroundColor White
Write-Host "  3. Adjust LED_COUNT in .env to match your setup" -ForegroundColor White
Write-Host "  4. Test the web interface and LED responsiveness" -ForegroundColor White
Write-Host "  5. Reboot the Pi for GPIO permissions to take full effect: sudo reboot" -ForegroundColor White
Write-Host ""
Write-Host "📚 For more information, see the project README and backend/tools/ documentation." -ForegroundColor Cyan