# Smart AutoPark - WebSocket Real-time System

Smart AutoPark is a Django-based parking management system with real-time WebSocket functionality for live updates and interactive features.

## Features

### Real-time WebSocket Functionality
- **Live Statistics Updates**: Real-time display of parking statistics (entries, exits, vehicles inside)
- **Date Filtering**: Filter data by specific dates with instant updates
- **Vehicle Entry Management**: View and manage vehicle entries in real-time
- **Payment Processing**: Mark vehicle entries as paid with instant feedback
- **Car Management**: Add cars with boolean flags (free, special taxi, blocked)
- **Car Blocking**: Block cars from entering the parking lot

### Core Features
- Vehicle entry and exit tracking
- Image capture for entry and exit
- Automatic fee calculation based on time spent
- User authentication and role management
- PostgreSQL database backend
- Redis for WebSocket channel layers

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Environment Variables**:
   Create a `.env` file with:
   ```
   SECRET_KEY=your_secret_key
   POSTGRES_DB=smartpark
   POSTGRES_USER=your_user
   POSTGRES_PASSWORD=your_password
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   ```

3. **Setup Redis** (required for WebSocket):
   ```bash
   # Install Redis
   sudo apt-get install redis-server
   
   # Start Redis
   sudo systemctl start redis
   ```

4. **Run Migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Start the Server**:
   ```bash
   python manage.py runserver
   ```

## WebSocket API

### Connection
Connect to: `ws://localhost:8000/ws/home/`

### Message Types

#### 1. Get Statistics
```json
{
  "type": "get_statistics",
  "date": "2024-01-01"
}
```

#### 2. Get Vehicle Entries
```json
{
  "type": "get_vehicle_entries",
  "date": "2024-01-01"
}
```

#### 3. Mark as Paid
```json
{
  "type": "mark_as_paid",
  "entry_id": 123
}
```

#### 4. Add Car
```json
{
  "type": "add_car",
  "number_plate": "30A123FA",
  "is_free": false,
  "is_special_taxi": true,
  "is_blocked": false
}
```

#### 5. Block Car
```json
{
  "type": "block_car",
  "number_plate": "30A123FA"
}
```

## Usage

1. **Access the Home Page**: Navigate to `/api/home/`
2. **Real-time Updates**: The page automatically connects to WebSocket and shows live data
3. **Date Filtering**: Use the date picker to filter data by specific dates
4. **Add Cars**: Click "Avtomobil qo'shish" to add cars with specific flags
5. **Block Cars**: Use the block form to prevent cars from entering
6. **Process Payments**: Click "To'lov" buttons to mark entries as paid

## Testing

Run the WebSocket test script:
```bash
python test_websocket.py
```

## API Endpoints

- `GET /api/statistics/` - Get parking statistics
- `GET /api/vehicle-entries/` - Get vehicle entries
- `POST /api/mark-paid/` - Mark entry as paid
- `POST /api/add-car/` - Add or update car
- `POST /api/block-car/` - Block a car

## Models

### VehicleEntry
- `number_plate`: Vehicle registration number
- `entry_time`: Entry timestamp
- `exit_time`: Exit timestamp (optional)
- `entry_image`: Entry photo
- `exit_image`: Exit photo (optional)
- `total_amount`: Parking fee
- `is_paid`: Payment status

### Cars
- `number_plate`: Vehicle registration number
- `is_free`: Free parking flag
- `is_special_taxi`: Special taxi flag
- `is_blocked`: Blocked status flag

## Configuration

- `HOUR_PRICE`: Parking fee per hour (default: 4000)
- Channel layers configured for Redis
- ASGI application with WebSocket support

## Development

The system uses:
- **Django Channels** for WebSocket support
- **Redis** for channel layers
- **PostgreSQL** for database
- **Tailwind CSS** for styling
