# Parallel Appium

An Appium server gateway hub that manages multiple Appium server processes for parallel testing on real devices. Similar in concept to Selenium Grid, this hub allows you to run multiple Appium sessions simultaneously, each with its own dedicated server process, port, and log file.

## Features

- **Parallel Testing**: Run multiple Appium sessions simultaneously on different devices
- **Session Management**: Automatic session creation, allocation, and cleanup
- **Isolated Logging**: Each session gets its own dedicated log file
- **Port Management**: Automatic port allocation from a configurable range
- **Health Monitoring**: Built-in health checks and session monitoring
- **REST API**: Full REST API for session management and monitoring
- **Pytest Integration**: Ready-to-use pytest-xdist examples for parallel test execution

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Test Client   │───▶│   Appium Hub     │───▶│ Appium Server 1 │
│   (pytest)     │    │   (Gateway)      │    │   (Port 4723)   │
└─────────────────┘    │                  │    └─────────────────┘
                       │                  │    ┌─────────────────┐
┌─────────────────┐    │                  │───▶│ Appium Server 2 │
│   Test Client   │───▶│  - Session Pool  │    │   (Port 4724)   │
│   (pytest)     │    │  - Port Manager  │    └─────────────────┘
└─────────────────┘    │  - Log Manager   │    ┌─────────────────┐
                       │                  │───▶│ Appium Server N │
                       │                  │    │   (Port 472N)   │
                       └──────────────────┘    └─────────────────┘
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd parallel-appim
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   ```

3. **Install Appium server** (if not already installed):
   ```bash
   npm install -g appium
   ```

4. **Install Appium drivers** (example for Android):
   ```bash
   appium driver install uiautomator2
   ```

## Quick Start

### 1. Start the Hub

```bash
# Using the startup script
python start_hub.py

# Or directly
python -m src.appium_hub.main

# With custom settings
python start_hub.py --port 4444 --max-sessions 5 --appium-port-start 4723 --appium-port-end 4773
```

### 2. Verify Hub is Running

```bash
curl http://localhost:4444/health
```

### 3. Run Parallel Tests

```bash
# Run tests with 4 parallel workers
pytest tests/ -n 4

# Run specific test file with 2 workers
pytest tests/test_simple_example.py -n 2 -v

# Run with custom hub URL
HUB_URL=http://localhost:4444 pytest tests/ -n 3
```

## Configuration

### Environment Variables

Create a `config.env` file (copy from `config.env.example`):

```bash
# Hub server settings
HUB_HOST=0.0.0.0
HUB_PORT=4444

# Appium server settings
APPIUM_PORT_START=4723
APPIUM_PORT_END=4773
MAX_SESSIONS=10
SESSION_TIMEOUT=1800

# Logging settings
LOG_DIR=logs
LOG_LEVEL=INFO
```

### Command Line Options

```bash
python start_hub.py --help
```

Options:
- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to bind to (default: 4444)
- `--appium-port-start`: Start of Appium port range (default: 4723)
- `--appium-port-end`: End of Appium port range (default: 4773)
- `--max-sessions`: Maximum concurrent sessions (default: 10)
- `--session-timeout`: Session timeout in seconds (default: 1800)
- `--log-dir`: Log directory (default: logs)
- `--log-level`: Log level (default: INFO)

## API Reference

### Hub Management

- `GET /` - Hub status and basic information
- `GET /health` - Health check with session statistics
- `GET /sessions` - List all active sessions

### Session Management

- `POST /session` - Create a new session
- `DELETE /session/{session_id}` - Delete a session
- `GET /session/{session_id}/info` - Get session information
- `ALL /session/{session_id}/{path}` - Proxy requests to Appium server

### Create Session Example

```bash
curl -X POST http://localhost:4444/session \
  -H "Content-Type: application/json" \
  -d '{
    "capabilities": {
      "platformName": "Android",
      "automationName": "UiAutomator2",
      "deviceName": "Android Device",
      "app": "/path/to/app.apk"
    },
    "device_name": "my_test_device"
  }'
```

Response:
```json
{
  "hub_session_id": "uuid-string",
  "appium_session": {...},
  "service_url": "http://127.0.0.1:4723"
}
```

## Testing Examples

### Basic Pytest Test

```python
import httpx
from appium import webdriver
from appium.options.android import UiAutomator2Options

def test_app_functionality():
    # Create session through hub
    with httpx.Client() as client:
        response = client.post(
            "http://localhost:4444/session",
            json={
                "capabilities": {
                    "platformName": "Android",
                    "automationName": "UiAutomator2",
                    "deviceName": "Test Device",
                    "app": "/path/to/app.apk"
                }
            }
        )
        session_data = response.json()
        service_url = session_data["service_url"]
    
    # Create Appium driver
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    
    driver = webdriver.Remote(service_url, options=options)
    
    # Your test code here
    driver.find_element("id", "button").click()
    
    driver.quit()
```

### Parallel Testing with pytest-xdist

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tests/ -n 4  # 4 parallel workers
pytest tests/ -n auto  # Auto-detect number of CPUs
```

## Log Management

Each session creates its own log file:
```
logs/
├── appium_hub.log                    # Hub main log
├── appium_server_{session_id}_{port}.log  # Individual session logs
└── ...
```

## Monitoring and Health Checks

### Health Endpoint

```bash
curl http://localhost:4444/health
```

Response:
```json
{
  "total_sessions": 3,
  "healthy_sessions": 3,
  "unhealthy_sessions": [],
  "available_ports": 47,
  "used_ports": [4723, 4724, 4725]
}
```

### Session List

```bash
curl http://localhost:4444/sessions
```

## Troubleshooting

### Common Issues

1. **Port conflicts:**
   - Ensure the Appium port range doesn't conflict with other services
   - Check that ports are available: `netstat -an | grep 4723`

2. **Session timeout:**
   - Increase `SESSION_TIMEOUT` if tests take longer than 30 minutes
   - Monitor session usage with `/sessions` endpoint

3. **Log file permissions:**
   - Ensure the log directory is writable
   - Check disk space for log files

4. **Appium server startup failures:**
   - Verify Appium is installed: `appium --version`
   - Check individual session logs in the logs directory

### Debug Mode

Run with debug logging:
```bash
python start_hub.py --log-level DEBUG
```

### Check Session Status

```bash
# List all sessions
curl http://localhost:4444/sessions

# Get specific session info
curl http://localhost:4444/session/{session_id}/info
```

## Development

### Project Structure

```
parallel-appim/
├── src/appium_hub/
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Main application entry point
│   ├── server_manager.py     # Individual Appium server management
│   ├── session_pool.py       # Session pool management
│   ├── gateway.py            # HTTP gateway/proxy
│   └── config.py             # Configuration management
├── tests/
│   ├── conftest.py           # Pytest configuration
│   ├── test_parallel_appium.py  # Comprehensive test examples
│   └── test_simple_example.py   # Simple test examples
├── logs/                     # Log files directory
├── pyproject.toml            # Project dependencies
├── pytest.ini               # Pytest configuration
├── start_hub.py              # Startup script
└── README.md                 # This file
```

### Running Tests

```bash
# Unit tests (if any)
pytest tests/ -m unit

# Integration tests
pytest tests/ -m integration

# All tests in parallel
pytest tests/ -n 4
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs in the `logs/` directory
3. Open an issue on the repository