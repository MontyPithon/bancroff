# User Management

## Overview
This project implements a user management system that integrates **Office365 authentication** using the Microsoft Authentication Library (MSAL). The system provides **CRUD operations** for managing users, **role-based access control (RBAC)**, and the ability to **deactivate/reactivate** user accounts. By combining Flask, SQLite, and MSAL, we ensure both secure authentication and straightforward user data handling.

---

## Technologies Used
- **Flask (Python):** Serves as the core web framework for handling routes and rendering templates.  
- **SQLite:** Stores user information, including name, email, role, and status.  
- **MSAL (Microsoft Authentication Library):** Manages Office365 sign-ins and token handling.  
- **WTForms:** Provides form validation and submission handling in Flask.  
- **HTML/CSS/Bootstrap (optional):** Powers the front-end for a user-friendly interface.

---

## Key Features

### 1. Office365 Authentication
- Users log in with their Office365 credentials.  
- The application uses MSAL to acquire tokens and validate user sessions.  
- Newly authenticated users are added to the local SQLite database with a default role of **basicuser**.

### 2. CRUD Operations
- **Create:** Administrators can add new user accounts through a form.  
- **Read:** Administrators can view a list of users, including name, email, role, and status.  
- **Update:** Administrators can modify user attributes, such as role and status.  
- **Delete:** Administrators can permanently remove user accounts when necessary.

### 3. Role-Based Access Control (RBAC)
- The system recognizes at least two roles: **basicuser** and **admin**.  
- Routes that alter user data are protected by an `admin_required` decorator.  
- Only users with the **admin** role can create, update, or delete other accounts.

### 4. User Deactivation & Reactivation
- Administrators can set a user’s status to **deactivated**.  
- Deactivated users are prevented from logging in or accessing protected routes.  
- The system also allows reactivating user accounts to restore access.

### 5. Session Management & Security
- Flask sessions store the user’s ID token and basic profile information after successful authentication.  
- Decorators like `active_user_required` ensure that only authenticated and active users can access restricted parts of the application.

---

## Implementation Details

### Database Schema
- A `users` table holds user data (`id`, `name`, `email`, `role`, `status`).  
- Future migrations or expansions (e.g., logging or audit tables) can be added as needed.

### Routes
- **`/login`**: Initiates Office365 login flow using MSAL.  
- **`/getAToken`**: Callback route that processes tokens and user info from Office365.  
- **`/logout`**: Logs the user out by clearing their session.  
- **`/users`**: Displays a list of users (admin-only).  
- **`/create_user`**: Form to create a new user (admin-only).  
- **`/update_user/<user_id>`**: Form to update an existing user (admin-only).  
- **`/delete_user/<user_id>`**: Endpoint to delete a user (admin-only).  
- **`/deactivate_user/<user_id>`**: Deactivates a user (admin-only).  
- **`/reactivate_user/<user_id>`**: Reactivates a user (admin-only).

### Decorators
- **`@active_user_required`**: Ensures the user is both logged in and active.  
- **`@admin_required`**: Checks that the user’s role is `admin` before allowing certain actions.

### Error Handling & Feedback
- The application uses Flask’s `flash` messages to inform users about the success or failure of operations.  
- Common errors (e.g., database issues, missing users) are gracefully handled and reported.

---

## Future Enhancements
- **Additional Roles**: Extend RBAC to include more granular roles (e.g., manager, auditor).  
- **Audit Logging**: Track changes to user records for compliance.  
- **Improved Front-End**: Use a JavaScript framework or additional Bootstrap styling to enhance usability.  
- **Scalability**: Switch from SQLite to a more robust database like PostgreSQL or MySQL for production environments.
