# ERC-Youth Application Summary

## Project Overview
This is a FastAPI-based web application designed for managing family information, likely for a religious organization or community. The application name "erc-youth" suggests it may be focused on youth or family ministry.

## Technical Architecture
- **Framework**: FastAPI with SQLAlchemy ORM
- **Authentication**: JWT-based authentication with bcrypt password hashing
- **Database**: SQL database (configured via DATABASE_URL)
- **File Storage**: Local filesystem for document storage

## Core Components

### 1. User Management
- Users have roles (admin, père/father, mère/mother, other)
- Parents have special permissions to manage family data
- Users are associated with families and can only access their own family's data
- Non-admin users receive a 4-digit access code as their initial password

### 2. Family Management
- Families are organized by category (Young, Mature) and name
- A family can have multiple users and family members
- Family members may not necessarily be system users

### 3. Family Member Management
- Detailed tracking of family members with personal information
- Information includes education level, employment status, and participation in church activities
- Members can be granted specific permissions (submit reports, view activities, etc.)

### 4. Activity Tracking
- Activities are categorized as Spiritual or Social
- Spiritual activities include prayer calendars, overnights, crusades, and agape events
- Social activities include contributions, illnesses, bereavements, weddings, and transfers
- Activities have statuses (planned, ongoing, completed, cancelled)

### 5. Document Management
- Families can upload and manage documents
- Documents are categorized as reports or letters
- Files are stored on the filesystem with unique identifiers

## Security Model
- Role-based access control (RBAC)
- Parent roles (père/mother) have special permissions
- JWT tokens for authentication with 60-minute expiration
- Password hashing with bcrypt
- Access codes for initial user access

## Development Status
The application appears to be functional but with some areas more developed than others:
- Family member management is comprehensive with full CRUD operations
- Document management includes file handling and full CRUD operations
- Activity management is more basic with only create and read operations implemented