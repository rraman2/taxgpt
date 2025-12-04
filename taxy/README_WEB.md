# Taxy Web UI

A web-based interface for managing tax scenarios with natural language input.

## Setup

1. **Install dependencies:**
   ```bash
   pip3 install flask flask-cors
   ```

2. **Run the web server:**
   ```bash
   cd taxy
   python3 web_ui.py
   ```

3. **Open in browser:**
   ```
   http://localhost:5001
   ```
   
   Note: If port 5001 is in use, you can specify a different port:
   ```bash
   PORT=8080 python3 web_ui.py
   ```
   Then open http://localhost:8080

## Features

- **Create Scenarios**: Click "Add New Scenario" to create a new tax scenario
- **Natural Language Input**: Enter scenarios in plain English (e.g., "Wage income $200K, married filing jointly, 2 dependent children")
- **Modify Scenarios**: Edit the description in any card to modify that scenario
- **Calculate Tax**: Click "Calculate Tax" button to compute tax liability
- **Restore**: Restore a scenario to its previous state
- **Delete**: Remove a scenario

## How It Works

1. **Base Scenario**: The first scenario you create is your base scenario
2. **Add Scenario**: Click "Add New Scenario" to create a new card/scenario
3. **Modify Card**: Edit the textarea in any card to modify that specific scenario
4. **Calculate**: Each scenario can be calculated independently

## API Endpoints

- `GET /api/scenarios` - List all scenarios
- `POST /api/scenarios` - Create new scenario
- `GET /api/scenarios/<id>` - Get specific scenario
- `PUT /api/scenarios/<id>` - Update scenario
- `POST /api/scenarios/<id>/calculate` - Calculate tax
- `POST /api/scenarios/<id>/restore` - Restore previous state
- `DELETE /api/scenarios/<id>` - Delete scenario

