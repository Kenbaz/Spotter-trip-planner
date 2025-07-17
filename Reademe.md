# SPOTTER HOS Trip Planner

## Authenticated Driver-Centric Compliance & Trip Calculator System

A comprehensive web application designed for **Spotter company drivers** to plan HOS-compliant trips, manage compliance records, and ensure DOT regulation adherence. The system provides an intuitive trip calculator that automatically ensures Hours of Service (HOS) compliance while offering fleet management capabilities through Django admin dashboard.

## Project Overview

**Primary Users:** Spotter truck drivers  
**Secondary Users:** Fleet managers (via Django admin)  
**Company:** Single-tenant system for Spotter company only

### Key Features

#### Driver-Focused Features
- **Authenticated Trip Calculator**: Secure, personal trip planning
- **HOS Compliance Automation**: Automatic break insertion and compliance checking
- **Personal Trip History**: Save, modify, and track personal trips
- **Real-time Compliance Status**: Dashboard showing current HOS status
- **Mobile-Friendly Interface**: Optimized for drivers on mobile devices
- **ELD Log Access**: View personal ELD logs via Django admin
- **Vehicle Integration**: Automatic vehicle assignment from fleet system

#### Fleet Management Features (Django Admin)
- **Driver Oversight**: Monitor all driver trips and compliance
- **Fleet Compliance Dashboard**: Company-wide compliance monitoring
- **Vehicle Assignment Management**: Assign drivers to vehicles
- **Reporting and Analytics**: Generate compliance and efficiency reports
- **Trip Approval Workflows**: Review and approve complex trips
- **Violation Tracking**: Monitor and address HOS violations

## Technical Architecture

### Tech Stack
- **Backend**: Django + Django REST Framework (API + Admin Dashboard)
- **Frontend**: React + TypeScript + Vite (Driver Interface)
- **Database**: PostgreSQL
- **Authentication**: JWT (Django Simple JWT)
- **Maps**: OpenStreetMap + Leaflet.js (React-Leaflet)
- **Routing**: OpenRouteService API (free tier)
- **Containerization**: Docker + Docker Compose
- **Admin Interface**: Django Admin (Fleet Management)
- **Static Files**: Django Whitenoise (production static file serving)

### Architecture Principles
- **Driver Authentication**: JWT-based login system
- **Trip Ownership**: Each trip belongs to a specific driver
- **Vehicle Integration**: Trips associated with driver's assigned vehicle
- **Role-Based Access**: Drivers see only their trips, fleet managers see all via admin
- **Company Context**: All data scoped to Spotter company automatically

## Project Structure

```
Trip-Planner/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .gitignore
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env
│   ├── manage.py
│   ├── Core_app/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── users/                          # User Management
│   │   ├── models.py                   # User, SpotterCompany, Vehicle, DriverVehicleAssignment
│   │   ├── views.py 
│   │   ├── admin.py                    # Fleet management dashboard
│   │   ├── serializers.py
│   │   ├── permissions.py
│   │   └── management/commands/
│   │       ├── create_admin.py
│   │       └── setup_admin_permissions.py
│   ├── trip_api/                       # Driver Trip Calculator
│   │   ├── models.py                   # Trip, Route, Stops, HOSPeriod, ComplianceReport
│   │   ├── views.py                    # Driver-focused trip API
│   │   ├── urls.py
│   │   ├── serializers.py
│   │   ├── admin.py                    # Trip monitoring for fleet managers
│   │   └── services/
│   │       ├── hos_calculator.py
│   │       ├── route_planner.py
│   │       ├── eld_generator.py
│   │       └── external_apis.py
│   ├── static/
│   └── tests/
└── frontend/                           # Driver Interface
    ├── Dockerfile
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── .env
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── components/
        │   ├── Auth/                   # Driver login/logout
        │   ├── Maps/                    # Route visualization
        │   ├── ELDLogs/               # ELD log management
        │   ├── Layout/
        |   ├── LazyComponents
        |   ├── SEO    
        │   └── UI/                     # Reusable components
        ├── services/
        |   ├── TripService
        |   ├── ELDService
        │   ├── authService.ts                 # Authentication service
        │   ├── apiClient.ts                  # Authenticated API calls
        │   └── MapService.ts
        ├── hooks/
        |   ├── useAddressInput.ts
        |   ├── useELDLogs.ts
        |   ├── useMap.ts
        |   ├── useTripQueries.ts
        │   ├── useAuth.ts              # Authentication hooks
        │   └── useTripCalculation.ts
        ├── pages/
        |   ├── CreateTripsPage.tsx
        |   ├── Dashboard.tsx
        |   ├── LoginPage.tsx
        |   ├── TripsDetailsPage.tsx
        |   ├── TripsPage.tsx
        ├── types/
        │   └── index.ts
        └── styles/
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 22+ (for local development)
- Python 3.10+ (for local development)

### Demo Access
The application includes a demo account for immediate testing:

**Demo Credentials:**
- Username: `John_Doe`
- Password: `@Johndriver1234`

Visit the login page and use the "Access Demo Account" button for instant access.

### Development Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd Trip-Planner
```

2. **Set up environment variables:**
```bash
# Backend
cp backend/.env
# Edit backend/.env with your configuration

# Frontend
cp frontend/.env
# Edit frontend/.env with your configuration
```

3. **Start the development environment:**
```bash
docker-compose up -d
```

4. **Run database migrations:**
```bash
docker-compose exec backend python manage.py migrate
```

5. **Create a superuser (optional):**
```bash
docker-compose exec backend python manage.py createsuperuser
```

6. **Access the application:**
- **Driver Interface**: http://localhost:3000
- **Admin Dashboard**: http://localhost:8000/admin


## Authentication & Security

### JWT Authentication
- Secure JWT-based authentication system
- Automatic token refresh mechanism
- Role-based access control (drivers vs fleet managers)
- Token expiration, validation, and refresh

### User Roles
- **Drivers**: Access to personal trips, compliance status, and ELD logs
- **Fleet Managers**: Full access via Django admin dashboard
- **Super Admins**: Complete system administration

### Data Security
- All data scoped to Spotter company automatically
- Drivers only see their own trip data
- Audit trails for all trip modifications
- Secure password requirements

## Core Features Deep Dive

### HOS Compliance Engine
- Real-time compliance validation
- Automatic break insertion based on DOT regulations
- Multi-day trip support with proper daily resets
- Violation detection

### Route Planning & Optimization
- Integration with OpenRouteService API
- Route optimization
- Interactive map with driver's current location

### ELD Log Generation
- Auto-population from trip planning data
- Driver certification and digital signatures


### Trip Management
- Personal trip history and tracking
- Trip duplication for recurring routes
- Real-time status updates
- Mobile-optimized interface

### Test Coverage
- Unit tests for HOS calculation logic
- Integration tests for API endpoints


## Monitoring & Performance

### Performance Optimizations
- Database query optimization
- Caching with Redis
- Efficient route calculation algorithms
- Mobile-optimized interface

### Monitoring
- Django admin for fleet management oversight
- Trip compliance monitoring

## Known Issues & Limitations

### Current Limitations
- Single company support (Spotter only)
- OpenRouteService API rate limits
- Mobile offline capabilities limited
- ELD Logs graph not implemented

### Planned Improvements
- Multi-company support
- Enhanced offline capabilities
- Advanced analytics dashboard
- Mobile app development
- ELD Graph implementation

## License

This project is proprietary software developed for Spotter company.