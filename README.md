# PATCUS VENTURES — Block Factory Management System

## Quick Start

1. Install dependencies:
   ```
   pip install flask pillow
   ```

2. Run the server:
   ```
   python app.py
   ```

3. Open browser at `http://localhost:5000`

## User Accounts & Roles

| Username   | Password  | Role                  | Access                                      |
|------------|-----------|----------------------|---------------------------------------------|
| sylvester  | osei17    | System Administrator | Full access: all tabs, delete records       |
| nanapoku   | patcus17  | Manager              | Add deliveries, payments, expenses, moulds  |
| sales1     | sales123  | Sales                | Add deliveries and record payments only     |

## Role Permissions

- **System Administrator** — Everything: view all, add all, delete all, admin panel
- **Manager** — View all, add deliveries / payments / expenses / production; no delete
- **Sales** — Add deliveries and record payments only

## File Structure

```
patcus/
├── app.py              ← Flask backend server
├── index.html          ← Main dashboard (served after login)
├── login.html          ← Login page
├── manifest.json       ← PWA manifest
├── service-worker.js   ← Offline PWA support
├── generate_icons.py   ← Run once to create app icons
└── patcus_data/        ← Auto-created data folder (JSON files)
```

## Generate Icons (optional, for PWA install)
```
python generate_icons.py
```

## Install as Mobile App (PWA)
1. Open `http://YOUR_IP:5000` on your phone
2. Tap menu → "Add to Home Screen"
3. Name it "PATCUS" and tap Add
