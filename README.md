# Team Bancroff - Form Approval System

Bancroff is a comprehensive form management and approval workflow system built with Flask. It allows for the creation, submission, and approval of various types of forms through a defined approval hierarchy.

## Features

- **User Authentication**: Microsoft OAuth integration for secure authentication
- **Role-Based Access Control**: Different access levels (admin, basic user, approval roles)
- **Form Management**: Support for multiple form types (currently RCL and Withdrawal forms)
- **Approval Workflows**: Multi-step approval processes with role-based assignments
- **User Management**: Admin interface for managing users and their roles
- **Signature Upload**: Support for digital signature uploads
- **PDF Generation**: Generation of properly signed PDF files at each step of the approval process

## Folder Structure

The application follows a modular structure:

```
bancroff/
├── app.py                  # Main application file
├── config.py               # Configuration settings
├── models/                 # Database models
│   ├── __init__.py
│   ├── user.py             # User and role models
│   └── request.py          # Request and approval models
├── forms/                  # Form definitions
│   ├── __init__.py
│   └── user_forms.py       # Form classes
├── routes/                 # Route handlers
│   ├── __init__.py
│   ├── auth.py             # Authentication routes
│   ├── user.py             # User management routes
│   ├── forms.py            # Form submission routes
│   └── approvals.py        # Approval workflow routes
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── auth_helpers.py     # Authentication helpers
│   └── data_helpers.py     # Database helpers
├── static/                 # Static files (CSS, JS)
├── templates/              # HTML templates
├── uploads/                # For uploaded files
├── pdf/                    # For PDF generation
│   ├── approval_template.tex  # LaTeX template for approval docs
│   └── Makefile            # For PDF compilation
├── Dockerfile              # Docker configuration
└── docker-compose.yml      # Docker Compose configuration
```

## Installation

### Prerequisites

- Python 3.13 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone the repository**

```bash
git clone https://github.com/MontyPithon/bancroff.git
cd bancroff
```

2. **Create and activate a virtual environment (recommended)**

```bash
# On Linux/macOS
python -m venv .venv
source .venv/bin/activate

# On Windows
python -m venv .venv
.venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Initialize the database**

The database will be automatically initialized when you first run the application.

5. **Run the application**

```bash
python app.py
```

The application will be available at http://localhost:50010 by default.

## Docker Installation

For a containerized setup, you can use Docker:

1. **Build and start the Docker container**

```bash
docker-compose up --build
```

2. **Stop the container**

```bash
docker-compose down
```

The Docker setup includes:
- Python 3.13 with all required dependencies
- LaTeX for PDF generation
- Proper volume mounts for persistent data
- Container configured to run on port 50010

### Docker Requirements

- Docker and Docker Compose installed on your system
- For PDF generation to work properly, the container includes:
  - LaTeX tools (texlive-latex-base, texlive-fonts-recommended, etc.)
  - Make for running the compilation process

## Usage

### Authentication

- Navigate to the login page and authenticate using your Microsoft account.
- On first login, users are assigned admin role by default.

### User Management (Admin Only)

- Navigate to the Users section to manage application users.
- Create, update, deactivate, or delete users as needed.
- Assign appropriate roles based on organizational hierarchy.

### Form Submission

1. Navigate to Available Forms
2. Select the form you want to submit
3. Fill out the form with required information
4. Submit the form to initiate the approval workflow

### Approval Process

1. Users with approval roles will see pending requests in their dashboard
2. Review the form submission details
3. Approve or reject the request with optional comments
4. The form moves to the next approval step if approved
5. PDFs are generated at each step of the approval process

## PDF Generation

The system generates PDF documents at each approval step using:
- LaTeX templates (in the pdf/ directory)
- User signatures from uploaded images
- Form data from each submission
- A Makefile that invokes pdflatex

The generated PDFs are stored and can be viewed or downloaded through the web interface.

## Customization

- Edit `config.py` to modify application settings including:
  - OAuth credentials
  - Database connection
  - File upload settings
  - Debug and server settings

## Troubleshooting

- For database issues, you can delete the `instance/bancroff.db` file and restart the application to recreate the database.
- Make sure the `uploads` and `pdf` directories exist and are writable.
- For Docker-related issues, check the logs using `docker-compose logs`.
- If PDF generation fails, ensure LaTeX is installed properly (included in Docker setup).

## Ideas for Future Development

### Form Builder Concept

- **Custom Form Creation**: Creating custom forms with various field types
- **Workflow Configuration**: Customizing approval workflows for each form
- **Role Assignment**: Assigning approval roles specific to each form type

This concept would allow administrators to create new form types without coding.

## License

This project is licensed under the terms specified in the LICENSE file.





